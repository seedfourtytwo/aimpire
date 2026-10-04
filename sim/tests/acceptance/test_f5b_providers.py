"""F5b acceptance: the Provider protocol and the offline providers (ADR-0005, ADR-0013).

Written by the planning model before implementation (ADR-0016). Read-only.

No network: Mock, Rule and Recorded are the only providers CI may use. A
provider never makes up a reply; a missing reply is an error outcome.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from aimpire.cognition.provider import (
    STATUSES,
    CognitionRequest,
    CognitionResult,
    MockFailure,
    MockProvider,
    ModelIdentity,
    Provider,
    RecordedProvider,
    RuleProvider,
    Usage,
)
from aimpire.cognition.recording import read_jsonl, write_jsonl
from aimpire.contracts.mind import MindReply, Observation, Policy

pytestmark = pytest.mark.acceptance

OBSERVATION = Observation.model_validate(
    {
        "contract": "m0",
        "civ_id": "C1",
        "decision_id": "D1",
        "version": "C1:c001:abcd1234",
        "calendar": {
            "tick": 10,
            "season": "SPRING",
            "year": 0,
            "council": 1,
            "ticks_to_next_council": 10,
        },
        "status": {
            "population": 30,
            "population_change": 0,
            "food_days": 12,
            "food_days_change": -3,
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

VALID_RAW = json.dumps(
    {
        "decision_id": "D1",
        "policy": {"allocations": [], "ration": 0},
        "orders": [{"kind": "FORAGE", "place": "PL01", "target": "", "qty": 5, "text": ""}],
        "messages": [],
        "commitments": [],
        "beliefs": [],
        "names": [],
        "journal": "Gather.",
        "annal": "",
    }
)


def _request(decision_id: str = "D1") -> CognitionRequest:
    return CognitionRequest(
        decision_id=decision_id,
        civ_id="C1",
        contract="m0",
        system="system text",
        observation=OBSERVATION,
        observation_text="observation text",
        reply_schema=MindReply.model_json_schema(),
        max_output_tokens=2000,
        timeout_s=30.0,
        effort=None,
        temperature=None,
    )


def _run(provider: Provider, decision_id: str = "D1") -> CognitionResult:
    return asyncio.run(provider.complete(_request(decision_id)))


def _floats(value: Any) -> list[Any]:
    if isinstance(value, float):
        return [value]
    if isinstance(value, dict):
        return [f for v in value.values() for f in _floats(v)]
    if isinstance(value, list):
        return [f for v in value for f in _floats(v)]
    return []


def _assert_int_fields(result: CognitionResult) -> None:
    for name in ("latency_ms", "attempts"):
        assert type(getattr(result, name)) is int, name
    for name in ("input_tokens", "output_tokens", "reasoning_tokens"):
        assert type(getattr(result.usage, name)) is int, name
    assert result.status in STATUSES


def _forage_rule(obs: Observation) -> MindReply:
    return MindReply.model_validate_json(VALID_RAW).model_copy(
        update={"decision_id": obs.decision_id, "policy": Policy(allocations=[], ration=0)}
    )


def test_recorded_provider_replays_exactly(tmp_path: Path):
    tricky = '{ "decision_id":"D1" ,\n\t"journal": "café \U0001f33e \\u00e9" }  \n'
    originals = {
        "D1": CognitionResult(
            raw_text=VALID_RAW + "  ",
            parsed=json.loads(VALID_RAW),
            status="ok",
            usage=Usage(input_tokens=1200, output_tokens=300, reasoning_tokens=50),
            model_reported="some-model-2026-01-01",
            latency_ms=4321,
            attempts=2,
        ),
        "D2": CognitionResult(
            raw_text=tricky,
            parsed=json.loads(tricky),
            status="schema_fail",
            usage=Usage(input_tokens=10, output_tokens=20, reasoning_tokens=0),
            model_reported="other",
            latency_ms=7,
            attempts=1,
        ),
        "D3": CognitionResult(
            raw_text="I can't help with that.",
            parsed=None,
            status="refusal",
            usage=Usage(input_tokens=5, output_tokens=6, reasoning_tokens=0),
            model_reported="other",
            latency_ms=9,
            attempts=1,
        ),
    }
    path = tmp_path / "decisions.jsonl"
    write_jsonl(path, originals)
    replayer = RecordedProvider(read_jsonl(path))
    for decision_id, original in originals.items():
        first = _run(replayer, decision_id)
        second = _run(replayer, decision_id)
        assert first.raw_text.encode("utf-8") == original.raw_text.encode("utf-8")
        assert first == second == original
        assert first.status == original.status
        assert first.usage == original.usage
        assert first.model_reported == original.model_reported
        assert (first.latency_ms, first.attempts) == (original.latency_ms, original.attempts)
        _assert_int_fields(first)
    assert _run(replayer, "D1").parsed == json.loads(VALID_RAW)
    assert _run(replayer, "D3").parsed is None


def test_recorded_provider_missing_decision_is_an_error():
    result = _run(RecordedProvider({}), "D9")
    assert result.status == "error"
    assert result.raw_text == "" and result.parsed is None


def test_mock_provider_never_invents_replies():
    mock = MockProvider({"D1": VALID_RAW})
    missing = _run(mock, "D2")
    assert missing.status == "error"
    assert missing.raw_text == "" and missing.parsed is None
    assert missing.usage == Usage(input_tokens=0, output_tokens=0, reasoning_tokens=0)


def test_mock_provider_returns_fixture_and_classifies():
    mock = MockProvider(
        {
            "ok": VALID_RAW,
            "float": VALID_RAW.replace('"qty": 5', '"qty": 5.0'),
            "nan": VALID_RAW.replace('"qty": 5', '"qty": NaN'),
            "prose": "Here is my plan: forage.",
            "array": "[1, 2]",
            "refused": MockFailure(status="refusal", raw_text="No."),
            "slow": MockFailure(status="timeout", raw_text=""),
        }
    )
    ok = _run(mock, "ok")
    assert ok.status == "ok" and ok.raw_text == VALID_RAW
    assert ok.parsed == json.loads(VALID_RAW)
    assert _run(mock, "float").status == "schema_fail"
    assert _run(mock, "nan").status == "schema_fail"
    assert _run(mock, "prose").status == "schema_fail" and _run(mock, "prose").parsed is None
    assert _run(mock, "array").parsed is None
    assert _run(mock, "refused").status == "refusal"
    assert _run(mock, "slow").status == "timeout"


def test_rule_provider_uses_the_same_reply_path():
    result = _run(RuleProvider(_forage_rule, name="forage"), "D1")
    assert result.status == "ok"
    assert result.parsed == json.loads(result.raw_text)
    assert MindReply.model_validate(result.parsed).decision_id == "D1"
    assert result.model_reported == "rule:forage"


def test_rule_provider_failure_is_an_error_not_a_reply():
    def broken(obs: Observation) -> MindReply:
        raise RuntimeError("bug in baseline")

    result = _run(RuleProvider(broken, name="broken"), "D1")
    assert result.status == "error"
    assert result.raw_text == "" and result.parsed is None


def test_results_never_carry_floats_into_state():
    providers: list[Provider] = [
        MockProvider({"D1": VALID_RAW}),
        RuleProvider(_forage_rule, name="forage"),
        RecordedProvider(
            {
                "D1": {
                    "raw_text": VALID_RAW,
                    "status": "ok",
                    "usage": {"input_tokens": 1, "output_tokens": 2, "reasoning_tokens": 0},
                    "model_reported": "m",
                    "latency_ms": 3,
                    "attempts": 1,
                }
            }
        ),
    ]
    for provider in providers:
        result = _run(provider)
        _assert_int_fields(result)
        assert result.status == "ok"
        assert _floats(result.parsed) == []


def test_providers_satisfy_protocol_and_cost_nothing():
    providers: list[object] = [
        MockProvider({}),
        RuleProvider(_forage_rule, name="forage"),
        RecordedProvider({}),
    ]
    for provider in providers:
        assert isinstance(provider, Provider)
        identity = provider.describe()
        assert isinstance(identity, ModelIdentity)
        assert identity.provider in {"mock", "rule", "recorded"}
        assert provider.estimate_max_cost_micro_usd(_request()) == 0
