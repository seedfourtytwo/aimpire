"""Unit tests for the live adapters, profiles and the suite's network guard (F6a, F6b)."""

import asyncio
import json
import socket
import traceback
from types import SimpleNamespace
from typing import Any

import httpx2
import pytest

from aimpire.cognition.anthropic_provider import AnthropicProvider
from aimpire.cognition.budget import Caps, Price
from aimpire.cognition.live_common import JSON_INSTRUCTION, input_token_bound, scrub
from aimpire.cognition.openai_compat import OpenAICompatProvider
from aimpire.cognition.profiles import ProfileError, parse_profile
from aimpire.cognition.protocol import CognitionRequest, CognitionResult
from aimpire.contracts.mind import MindReply, Observation
from tests.conftest import NetworkBlocked

LOCAL = """
kind = "openai_compat"
model = "qwen3:8b"
base_url = "http://localhost:11434/v1"
api_key_env = ""
structured_output = "{mode}"
timeout_s = 30
max_output_tokens = 500

[price]
input_micro_usd_per_mtok = {price_in}
output_micro_usd_per_mtok = {price_out}
source = "test"
as_of = "2026-10-04"

[budget]
max_input_tokens_per_call = 4000
"""


def _local(mode: str = "json_schema", price_in: int = 0, price_out: int = 0) -> Any:
    text = LOCAL.format(mode=mode, price_in=price_in, price_out=price_out)
    return parse_profile(text, name="local")


def _request(max_output_tokens: int = 1000) -> CognitionRequest:
    observation = Observation.model_validate(
        {
            "contract": "m0",
            "civ_id": "C1",
            "decision_id": "C1-K0001",
            "version": "v",
            "calendar": {
                "tick": 0,
                "season": "S0",
                "year": 0,
                "council": 1,
                "ticks_to_next_council": 10,
            },
            "status": {
                "population": 1,
                "population_change": 0,
                "food_days": 1,
                "food_days_change": 0,
                "stores": [],
            },
            "places": [],
            "events": [],
            "messages": [],
            "standing": {
                "policy": {"allocations": [], "ration": 1000},
                "tasks": [],
                "commitments": [],
            },
            "last_results": [],
            "knowledge": {"claims": [], "beliefs": []},
            "journal": "",
        }
    )
    return CognitionRequest(
        decision_id="C1-K0001",
        civ_id="C1",
        contract="m0",
        system="sys",
        observation=observation,
        observation_text="obs",
        reply_schema=MindReply.model_json_schema(),
        max_output_tokens=max_output_tokens,
        timeout_s=10.0,
        effort=None,
        temperature=None,
    )


def _run(provider: Any, req: CognitionRequest | None = None) -> CognitionResult:
    return asyncio.run(provider.complete(req or _request()))


def _respond(body: dict[str, Any]) -> httpx2.MockTransport:
    return httpx2.MockTransport(lambda r: httpx2.Response(200, json=body))


def _choice(content: Any, finish: str = "stop", **message: Any) -> dict[str, Any]:
    return {
        "model": "qwen3:8b",
        "choices": [
            {
                "finish_reason": finish,
                "message": {"role": "assistant", "content": content, **message},
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }


# --- OpenAI-compatible ---------------------------------------------------------


def test_local_profile_sends_no_authorization_header():
    seen: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, json=_choice("{}"))

    _run(OpenAICompatProvider(_local(), transport=httpx2.MockTransport(handle)))
    assert "authorization" not in seen[0].headers
    assert str(seen[0].url) == "http://localhost:11434/v1/chat/completions"


@pytest.mark.parametrize("mode", ["json_object", "prompt"])
def test_fallback_modes_put_the_schema_in_the_system_message(mode: str):
    provider = OpenAICompatProvider(_local(mode))
    body = provider.request_body(_request())
    system = body["messages"][0]["content"]
    assert system.startswith("sys\n\n" + JSON_INSTRUCTION)
    assert json.loads(system.split("\n", 3)[3]) == MindReply.model_json_schema()
    if mode == "json_object":
        assert body["response_format"] == {"type": "json_object"}
    else:
        assert "response_format" not in body
    assert body["max_tokens"] == 500  # the smaller of request (1000) and profile (500)


def test_refusal_and_truncation_keep_their_usage():
    result = _run(OpenAICompatProvider(_local(), transport=_respond(_choice(None, refusal="no"))))
    assert (result.status, result.raw_text, result.usage.input_tokens) == ("refusal", "no", 10)
    filtered = _choice("x", finish="content_filter")
    assert _run(OpenAICompatProvider(_local(), transport=_respond(filtered))).status == "refusal"
    cut = _run(OpenAICompatProvider(_local(), transport=_respond(_choice('{"a"', "length"))))
    assert (cut.status, cut.raw_text, cut.usage.output_tokens) == ("truncated", '{"a"', 5)


def test_error_envelope_with_status_200_is_an_error():
    body = {"error": {"code": 502, "message": "upstream failed"}}
    result = _run(OpenAICompatProvider(_local(), transport=_respond(body)))
    assert result.status == "error"
    assert "upstream failed" in result.raw_text


def test_priced_call_without_usage_is_charged_its_worst_case():
    body = _choice("{}")
    del body["usage"]
    profile = _local(price_in=1_000_000, price_out=2_000_000)
    provider = OpenAICompatProvider(profile, transport=_respond(body))
    result = _run(provider)
    req = _request()
    assert result.usage.input_tokens == input_token_bound(req)
    assert result.usage.output_tokens == 500
    assert profile.price.cost(result.usage) == provider.estimate_max_cost_micro_usd(req)


def test_free_local_model_estimates_zero():
    assert OpenAICompatProvider(_local()).estimate_max_cost_micro_usd(_request()) == 0


def test_connection_failure_is_an_error():
    def fail(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("refused", request=request)

    result = _run(OpenAICompatProvider(_local(), transport=httpx2.MockTransport(fail)))
    assert (result.status, result.raw_text) == ("error", "ConnectError")


# --- Anthropic -------------------------------------------------------------------


def test_anthropic_sends_effort_and_temperature_only_when_set(monkeypatch: pytest.MonkeyPatch):
    text = """
kind = "anthropic"
model = "m"
api_key_env = "K_FOR_TEST"
timeout_s = 5
max_output_tokens = 100
effort = "low"
temperature = 1.0
[price]
input_micro_usd_per_mtok = 1
output_micro_usd_per_mtok = 1
source = "s"
as_of = "d"
[budget]
max_input_tokens_per_call = 10
"""
    params = AnthropicProvider(parse_profile(text, "a")).request_params(_request())
    assert params["output_config"]["effort"] == "low"
    assert params["extra_body"] == {"temperature": 1.0}
    assert params["max_tokens"] == 100
    plain = text.replace('effort = "low"\n', "").replace("temperature = 1.0\n", "")
    params = AnthropicProvider(parse_profile(plain, "a")).request_params(_request())
    assert "effort" not in params["output_config"]
    assert "extra_body" not in params


def test_anthropic_without_usage_charges_worst_case(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("K_FOR_TEST", "k" * 20)
    text = """
kind = "anthropic"
model = "m"
api_key_env = "K_FOR_TEST"
timeout_s = 5
max_output_tokens = 100
[price]
input_micro_usd_per_mtok = 1
output_micro_usd_per_mtok = 1
source = "s"
as_of = "d"
[budget]
max_input_tokens_per_call = 10
"""
    message = SimpleNamespace(
        model="m", stop_reason="end_turn", content=[SimpleNamespace(type="text", text="{}")]
    )

    class Fake:
        def __init__(self) -> None:
            self.messages = self

        async def create(self, **kwargs: Any) -> Any:
            return message

    provider = AnthropicProvider(parse_profile(text, "a"), client_factory=lambda key: Fake())
    result = _run(provider)
    assert result.status == "schema_fail"
    assert result.usage.output_tokens == 100


# --- Profiles ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ('base_url = "http://localhost:11434/v1"', 'base_url = "https://x.example/v1"', "price"),
        ('kind = "openai_compat"', 'kind = "gemini"', "kind"),
        ("timeout_s = 30", "timeout_s = 0", "timeout_s"),
        ("max_output_tokens = 500", "max_output_tokens = 0", "max_output_tokens"),
        ('structured_output = "json_schema"', 'structured_output = "xml"', "structured_output"),
        ("max_input_tokens_per_call = 4000", "", "max_input_tokens_per_call"),
        ('api_key_env = ""', 'api_key_env = "BAD-NAME"', "api_key_env"),
        ("[budget]", 'effort = "high"\n[budget]', "effort"),
        ('base_url = "http://localhost:11434/v1"', 'base_url = "http://u:p@localhost/v1"', "cred"),
    ],
)
def test_profile_errors(old: str, new: str, message: str):
    text = LOCAL.format(mode="json_schema", price_in=0, price_out=0).replace(old, new)
    with pytest.raises(ProfileError, match=message):
        parse_profile(text, name="bad")


def test_run_cap_may_only_go_down():
    base = LOCAL.format(mode="json_schema", price_in=0, price_out=0)
    lower = parse_profile(base + "run_cap_micro_usd = 500_000\n", name="p")
    assert lower.caps() == Caps(run_micro_usd=500_000)
    with pytest.raises(ProfileError, match="lower"):
        parse_profile(base + "run_cap_micro_usd = 2_000_001\n", name="p")


def test_planning_worst_case_uses_the_budget_estimate():
    profile = _local(price_in=1_000_000, price_out=4_000_000)
    assert profile.price == Price(1_000_000, 4_000_000)
    assert profile.worst_case_call_micro_usd() == 4000 + 500 * 4


def test_scrub_removes_raw_and_escaped_secret():
    secret = 'abc"def\\ghi'
    text = f"x {secret} y {json.dumps(secret)[1:-1]}"
    assert secret not in scrub(text, secret)
    assert json.dumps(secret)[1:-1] not in scrub(text, secret)


# --- The network guard -------------------------------------------------------------


def test_real_sockets_are_blocked():
    with pytest.raises(NetworkBlocked):
        socket.create_connection(("127.0.0.1", 9), timeout=1)


def test_real_http_client_cannot_reach_a_provider():
    async def call() -> None:
        async with httpx2.AsyncClient() as client:
            await client.get("http://127.0.0.1:9/")

    with pytest.raises(Exception) as caught:  # anyio may wrap it in an ExceptionGroup
        asyncio.run(call())
    assert "NetworkBlocked" in "".join(traceback.format_exception(caught.value))
