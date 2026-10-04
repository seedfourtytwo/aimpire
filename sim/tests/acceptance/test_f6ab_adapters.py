"""F6a/F6b acceptance: live provider adapters and model profiles (ADR-0005, ADR-0013, ADR-0014).

Written in the planning role before implementation (ADR-0016). Read-only.

* ``OpenAICompatProvider`` speaks the OpenAI-compatible chat completions API
  (Ollama, llama.cpp ``llama-server``, OpenRouter). A reply goes through the
  same ``parse_reply`` and validator path as every other provider.
* ``AnthropicProvider`` uses the official SDK; its client is injected here.
* Every failure is one of the existing outcomes: a schema-invalid reply is
  ``INVALID``, a timeout ``TIMEOUT``, a refusal ``REFUSAL``. Nothing crashes.
* Cost is charged from the usage the provider reports, at the profile's price.
* Keys are read from the environment by name at call time. A planted key
  never appears in error text, results or the run store. A missing key is a
  clear refusal before any call is made.
* A profile whose model is still a placeholder is refused by the loader.

No network: the OpenAI-compatible adapter gets an ``httpx2.MockTransport``
(httpx2 is the maintained httpx continuation the Anthropic SDK is built on)
and the Anthropic adapter a fake client. ``tests/conftest.py`` also blocks
real sockets for the whole suite.
"""

import asyncio
import json
import sqlite3
from collections.abc import Callable
from compression import zstd
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import numpy as np
import pytest

from aimpire.cognition.anthropic_provider import AnthropicProvider
from aimpire.cognition.budget import BudgetGuard, Caps, Price
from aimpire.cognition.council import SeatCall, Settled, decision_id_for, hold_council
from aimpire.cognition.live import provider_from_profile
from aimpire.cognition.openai_compat import OpenAICompatProvider
from aimpire.cognition.profiles import (
    MissingCredential,
    Profile,
    ProfileError,
    load_profile,
    parse_profile,
)
from aimpire.cognition.protocol import CognitionRequest, Provider
from aimpire.contracts.mind import MindReply, Observation
from aimpire.persistence.store import RunStore
from aimpire.sim.actions import CouncilSeat, DecisionLog, Outcome
from aimpire.sim.actions.commit import CIV_KIND, standing_policy_of
from aimpire.sim.state import Value, WorldState

pytestmark = pytest.mark.acceptance

REPO = Path(__file__).resolve().parents[3]
SEED = 77
CIV = "C1"
PLACES = frozenset({"PL01", "PL02"})
KEY_ENV = "AIMPIRE_F6_TEST_KEY"  # deliberately not "*API_KEY": the adapter itself must not leak
PLANTED = "planted-Zq8vX2-not-a-real-key-31337"

OPENROUTER_TOML = f"""
kind = "openai_compat"
model = "vendor/some-model"
base_url = "https://openrouter.ai/api/v1"
api_key_env = "{KEY_ENV}"
structured_output = "json_schema"
timeout_s = 30.0
max_output_tokens = 1000

[price]
input_micro_usd_per_mtok = 1_000_000
output_micro_usd_per_mtok = 5_000_000
source = "test fixture"
as_of = "2026-10-04"

[budget]
max_input_tokens_per_call = 4000
"""

ANTHROPIC_TOML = f"""
kind = "anthropic"
model = "claude-test-model"
api_key_env = "{KEY_ENV}"
timeout_s = 30.0
max_output_tokens = 1000

[price]
input_micro_usd_per_mtok = 1_000_000
output_micro_usd_per_mtok = 5_000_000
source = "test fixture"
as_of = "2026-10-04"

[budget]
max_input_tokens_per_call = 4000
"""


# --- A one-civilization world and its seat -----------------------------------


def _world() -> tuple[WorldState, int]:
    state = WorldState(run_seed=SEED, rules_version="v1", rules_hash="rules-hash")
    state.add_layer("food", np.zeros((2, 2), dtype=np.int64))
    policy: Value = {"allocations": [], "ration": 1000}
    entity = state.add_entity(CIV_KIND, {"civ_id": CIV, "policy": policy, "journal": ""})
    return state, entity


def _observation(decision_id: str, version: str) -> Observation:
    return Observation.model_validate(
        {
            "contract": "m0",
            "civ_id": CIV,
            "decision_id": decision_id,
            "version": version,
            "calendar": {
                "tick": 0,
                "season": "S0",
                "year": 0,
                "council": 1,
                "ticks_to_next_council": 10,
            },
            "status": {
                "population": 10,
                "population_change": 0,
                "food_days": 5,
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


def _request(decision_id: str, version: str) -> CognitionRequest:
    return CognitionRequest(
        decision_id=decision_id,
        civ_id=CIV,
        contract="m0",
        system="You are a council.",
        observation=_observation(decision_id, version),
        observation_text="tick 0",
        reply_schema=MindReply.model_json_schema(),
        max_output_tokens=1000,
        timeout_s=30.0,
        effort=None,
        temperature=None,
    )


def _call(state: WorldState, entity: int, provider: Provider, price: Price) -> SeatCall:
    decision_id = decision_id_for(CIV, 1)
    version = f"{CIV}:c001"
    seat = CouncilSeat(
        civ_id=CIV,
        decision_id=decision_id,
        council=1,
        observation_version=version,
        known_places=PLACES,
        people=10,
        known_civs=frozenset(),
        evidence_ids=frozenset(),
        policy=standing_policy_of(state.entities[entity]),
    )
    return SeatCall(entity, seat, _request(decision_id, version), provider, price)


def _council(provider: Provider, price: Price, guard: BudgetGuard | None = None) -> Settled:
    state, entity = _world()
    gate = guard if guard is not None else BudgetGuard(Caps())
    (settled,) = asyncio.run(
        hold_council(state, [_call(state, entity, provider, price)], gate=gate, log=DecisionLog())
    )
    return settled


def _reply_json(decision_id: str = "C1-K0001") -> str:
    return json.dumps(
        {
            "decision_id": decision_id,
            "policy": {
                "allocations": [{"activity": "FORAGE", "place": "PL01", "share": 500}],
                "ration": 900,
            },
            "orders": [],
            "messages": [],
            "commitments": [],
            "beliefs": [],
            "names": [],
            "journal": "we gather",
            "annal": "",
        }
    )


# --- OpenAI-compatible mocks --------------------------------------------------


Handler = Callable[[httpx2.Request], httpx2.Response]


def _chat(
    content: str, *, prompt: int = 1000, completion: int = 200, reasoning: int = 0
) -> Handler:
    def handle(request: httpx2.Request) -> httpx2.Response:
        body = {
            "id": "gen-1",
            "object": "chat.completion",
            "model": "vendor/some-model",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "total_tokens": prompt + completion,
                "completion_tokens_details": {"reasoning_tokens": reasoning},
            },
        }
        return httpx2.Response(200, json=body)

    return handle


class _Recorder:
    """A mock transport handler that remembers every request it saw."""

    def __init__(self, handler: Handler) -> None:
        self.handler = handler
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return self.handler(request)


def _openai(
    handler: Handler, toml: str = OPENROUTER_TOML
) -> tuple[OpenAICompatProvider, _Recorder]:
    recorder = _Recorder(handler)
    profile = parse_profile(toml, name="test-openrouter")
    provider = OpenAICompatProvider(profile, transport=httpx2.MockTransport(recorder))
    return provider, recorder


@pytest.fixture
def key(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv(KEY_ENV, PLANTED)
    return PLANTED


# --- F6a: OpenAI-compatible ---------------------------------------------------


def test_openai_compat_reply_parses_and_validates(key: str):
    provider, recorder = _openai(_chat(_reply_json()))
    settled = _council(provider, parse_profile(OPENROUTER_TOML, name="p").price)

    assert settled.result is not None
    assert settled.result.status == "ok"
    assert settled.record.outcome is Outcome.VALID
    # One POST to <base_url>/chat/completions, asking for the reply schema.
    (sent,) = recorder.requests
    assert sent.method == "POST"
    assert str(sent.url) == "https://openrouter.ai/api/v1/chat/completions"
    body = json.loads(sent.content)
    assert body["model"] == "vendor/some-model"
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["schema"] == MindReply.model_json_schema()
    assert sent.headers["authorization"] == f"Bearer {key}"


def test_openai_compat_schema_invalid_reply_is_invalid_not_a_crash(key: str):
    broken = json.loads(_reply_json())
    broken["policy"]["ration"] = 0.5  # floats are refused by the strict contract
    provider, _ = _openai(_chat(json.dumps(broken)))
    settled = _council(provider, Price(0, 0))

    assert settled.result is not None
    assert settled.result.status == "schema_fail"
    assert settled.record.outcome is Outcome.INVALID

    provider, _ = _openai(_chat("I think we should forage."))
    assert _council(provider, Price(0, 0)).record.outcome is Outcome.INVALID


def test_openai_compat_timeout_is_timeout_outcome(key: str):
    def slow(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("timed out", request=request)

    provider, _ = _openai(slow)
    settled = _council(provider, Price(0, 0))
    assert settled.result is not None
    assert settled.result.status == "timeout"
    assert settled.record.outcome is Outcome.TIMEOUT


def test_openai_compat_http_error_is_provider_error(key: str):
    provider, _ = _openai(lambda r: httpx2.Response(502, json={"error": {"message": "bad"}}))
    assert _council(provider, Price(0, 0)).record.outcome is Outcome.PROVIDER_ERROR


def test_cost_is_charged_from_reported_usage(key: str):
    profile = parse_profile(OPENROUTER_TOML, name="p")
    # 1000 input at $1/MTok + (150 output + 50 reasoning) at $5/MTok = 1000 + 1000 micro-dollars.
    provider, _ = _openai(_chat(_reply_json(), prompt=1000, completion=200, reasoning=50))
    guard = BudgetGuard(Caps())
    settled = _council(provider, profile.price, guard)

    assert settled.result is not None
    usage = settled.result.usage
    assert (usage.input_tokens, usage.output_tokens, usage.reasoning_tokens) == (1000, 150, 50)
    assert settled.charged == 2000
    assert guard.spent_run == 2000
    assert guard.held == 0
    # The reservation was a real worst case: at least the full output cap at the output price.
    assert settled.grant.reserved >= 1000 * 5_000_000 // 1_000_000


def test_missing_key_is_refused_before_any_call(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(KEY_ENV, raising=False)
    recorder = _Recorder(_chat(_reply_json()))
    profile = parse_profile(OPENROUTER_TOML, name="test-openrouter")

    with pytest.raises(MissingCredential) as refused:
        provider_from_profile(profile, transport=httpx2.MockTransport(recorder))
    assert KEY_ENV in str(refused.value)  # names the variable to set
    assert recorder.requests == []

    # A key removed after the provider was built is also refused at call time, without a call.
    provider = OpenAICompatProvider(profile, transport=httpx2.MockTransport(recorder))
    settled = _council(provider, profile.price)
    assert settled.record.outcome is Outcome.PROVIDER_ERROR
    assert recorder.requests == []


def _all_bytes(root: Path) -> list[bytes]:
    out: list[bytes] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            out.append(zstd.decompress(data) if path.name.endswith(".zst") else data)
    return out


def test_planted_key_never_leaks(key: str, tmp_path: Path):
    def echo_auth(request: httpx2.Request) -> httpx2.Response:
        # A hostile or buggy server that echoes the credentials back in its error.
        auth = request.headers.get("authorization", "")
        return httpx2.Response(401, json={"error": {"message": f"bad key: {auth}"}})

    provider, recorder = _openai(echo_auth)
    assert recorder.requests == []
    for text in (repr(provider), str(provider)):
        assert key not in text

    state, entity = _world()
    store = RunStore.create(
        tmp_path / "run",
        run_id="leak",
        seed=SEED,
        rules_version="v1",
        rules_hash="rules-hash",
        caps=Caps(),
        month="2026-10",
    )
    calls = [_call(state, entity, provider, Price(0, 0))]
    settled = asyncio.run(hold_council(state, calls, gate=store.budget_guard(0), log=DecisionLog()))
    store.record_council(0, 1, settled)
    store.checkpoint(state, "barrier")
    store.close()

    assert recorder.requests  # the key really was sent, and echoed back
    (item,) = settled
    assert item.record.outcome is Outcome.PROVIDER_ERROR
    assert item.result is not None
    assert key not in item.result.raw_text
    assert key not in repr(item.result)
    for blob in _all_bytes(tmp_path / "run"):
        assert key.encode() not in blob
    db = sqlite3.connect(tmp_path / "run" / "run.db")
    dump = "\n".join(db.iterdump())
    db.close()
    assert key not in dump

    with pytest.raises(MissingCredential) as refused:
        provider_from_profile(parse_profile(OPENROUTER_TOML.replace(KEY_ENV, "NOPE_UNSET"), "x"))
    assert key not in str(refused.value)


# --- F6b: Anthropic -----------------------------------------------------------


class _FakeMessages:
    def __init__(self, respond: Callable[[dict[str, Any]], Any]) -> None:
        self.respond = respond
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self.respond(kwargs)


class _FakeAnthropic:
    """Stands in for ``anthropic.AsyncAnthropic``: only ``messages.create`` is used."""

    def __init__(self, respond: Callable[[dict[str, Any]], Any]) -> None:
        self.messages = _FakeMessages(respond)
        self.keys: list[str] = []

    def factory(self, api_key: str) -> Any:
        self.keys.append(api_key)
        return self


def _message(text: str, stop_reason: str = "end_turn", thinking: int = 0) -> Any:
    return SimpleNamespace(
        id="msg_1",
        model="claude-test-model",
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(
            input_tokens=1000,
            output_tokens=200,
            output_tokens_details=SimpleNamespace(thinking_tokens=thinking),
        ),
    )


def _anthropic(
    respond: Callable[[dict[str, Any]], Any],
) -> tuple[AnthropicProvider, _FakeAnthropic]:
    fake = _FakeAnthropic(respond)
    profile = parse_profile(ANTHROPIC_TOML, name="test-anthropic")
    return AnthropicProvider(profile, client_factory=fake.factory), fake


def test_anthropic_reply_parses_validates_and_is_charged(key: str):
    provider, fake = _anthropic(lambda kw: _message(_reply_json(), thinking=40))
    guard = BudgetGuard(Caps())
    settled = _council(provider, parse_profile(ANTHROPIC_TOML, name="p").price, guard)

    assert settled.record.outcome is Outcome.VALID
    (sent,) = fake.messages.calls
    assert sent["model"] == "claude-test-model"
    assert sent["output_config"]["format"] == {
        "type": "json_schema",
        "schema": MindReply.model_json_schema(),
    }
    assert fake.keys == [key]
    assert settled.result is not None
    usage = settled.result.usage
    assert (usage.input_tokens, usage.output_tokens, usage.reasoning_tokens) == (1000, 160, 40)
    assert settled.charged == 2000  # 1000 at $1/MTok + 200 billed output at $5/MTok


@pytest.mark.parametrize(
    ("stop_reason", "outcome"),
    [("refusal", Outcome.REFUSAL), ("max_tokens", Outcome.TRUNCATED)],
)
def test_anthropic_stop_reasons_map_to_outcomes(key: str, stop_reason: str, outcome: Outcome):
    provider, _ = _anthropic(lambda kw: _message(_reply_json(), stop_reason=stop_reason))
    assert _council(provider, Price(0, 0)).record.outcome is outcome


def test_anthropic_timeout_and_errors_are_outcomes(key: str):
    def timeout(kw: dict[str, Any]) -> Any:
        raise anthropic.APITimeoutError(request=httpx2.Request("POST", "https://api.invalid/"))

    provider, _ = _anthropic(timeout)
    assert _council(provider, Price(0, 0)).record.outcome is Outcome.TIMEOUT

    def broken(kw: dict[str, Any]) -> Any:
        raise anthropic.APIConnectionError(
            message=f"failed with {PLANTED}", request=httpx2.Request("POST", "https://api.invalid/")
        )

    provider, _ = _anthropic(broken)
    settled = _council(provider, Price(0, 0))
    assert settled.record.outcome is Outcome.PROVIDER_ERROR
    assert settled.result is not None
    assert key not in settled.result.raw_text

    provider, _ = _anthropic(lambda kw: _message("not json"))
    assert _council(provider, Price(0, 0)).record.outcome is Outcome.INVALID


# --- Profiles -----------------------------------------------------------------


def test_placeholder_model_is_refused():
    toml = OPENROUTER_TOML.replace('"vendor/some-model"', '"REPLACE_WITH_VERIFIED_MODEL_ID"')
    with pytest.raises(ProfileError, match="placeholder"):
        parse_profile(toml, name="template")


def test_profile_holds_only_the_key_name(key: str):
    profile = parse_profile(OPENROUTER_TOML, name="p")
    assert isinstance(profile, Profile)
    assert profile.api_key_env == KEY_ENV
    assert key not in repr(profile)
    with pytest.raises(ProfileError):
        parse_profile(OPENROUTER_TOML.replace(f'api_key_env = "{KEY_ENV}"', 'api_key = "x"'), "p")


def test_example_ollama_profile_is_local_and_free():
    profile = load_profile(REPO / "profiles" / "ollama-example.toml")
    assert profile.kind == "openai_compat"
    assert profile.base_url == "http://localhost:11434/v1"
    assert profile.price == Price(0, 0)
    for path in sorted((REPO / "profiles").glob("*.toml")):
        text = path.read_text(encoding="utf-8")
        if "REPLACE_WITH_" in text:
            with pytest.raises(ProfileError):
                load_profile(path)
        else:
            load_profile(path)
