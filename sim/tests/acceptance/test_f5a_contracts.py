"""F5a acceptance: the m0 mind contract and its exported JSON schemas (ADR-0013).

Written by the planning model before implementation (ADR-0016). Read-only.

The reply schema is what a provider's structured-output mode constrains the
model to. ADR-0013 requires one schema that works on every provider, so it may
contain no optional and no union-typed fields. Anthropic's documented limits
(24 optional, 16 union-typed parameters per request) are the ceiling; the
contract aims for zero of each.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from aimpire.contracts.export import render_schemas
from aimpire.contracts.mind import CONTRACT_VERSION, MindReply, Observation

pytestmark = pytest.mark.acceptance

SCHEMA_DIR = Path(__file__).resolve().parents[3] / "schema"
REPLY_FILE = "mind-m0.reply.schema.json"
OBSERVATION_FILE = "mind-m0.observation.schema.json"
ANTHROPIC_MAX_OPTIONAL = 24
ANTHROPIC_MAX_UNION = 16

EXAMPLE_REPLY: dict[str, Any] = {
    "decision_id": "D000012",
    "policy": {
        "allocations": [{"activity": "FORAGE", "place": "PL07", "share": 600}],
        "ration": 1000,
    },
    "orders": [{"kind": "SCOUT", "place": "PL11", "target": "", "qty": 2, "text": ""}],
    "messages": [{"to": "VOICE", "text": "We ask for rain."}],
    "commitments": [{"kind": "STOCK_AT_LEAST", "place": "", "qty": 400, "by_council": 9}],
    "beliefs": [{"statement": "Berries return after rain.", "evidence": ["EV0450"]}],
    "names": [{"id": "PL07", "name": "Red Hollow"}],
    "journal": "Food is short. Scouts go north.",
    "annal": "The band sent scouts north.",
}


def _walk(node: Any, path: str = "$"):
    """Yield (path, dict) for every JSON object node in a schema."""
    if isinstance(node, dict):
        yield path, node
        for key, value in node.items():
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _walk(value, f"{path}[{i}]")


def _reply_schema() -> dict[str, Any]:
    return json.loads(render_schemas()[REPLY_FILE])


def test_contract_version_is_m0():
    assert CONTRACT_VERSION == "m0"


def test_reply_schema_has_no_optional_or_union_fields():
    schema = _reply_schema()
    optional = 0
    union = 0
    objects = 0
    for path, node in _walk(schema):
        if "anyOf" in node or "oneOf" in node or "allOf" in node:
            union += 1
        if isinstance(node.get("type"), list):
            union += 1
        if node.get("type") == "object":
            objects += 1
            assert node.get("additionalProperties") is False, f"{path}: extra fields allowed"
            props = set(node.get("properties", {}))
            required = set(node.get("required", []))
            optional += len(props - required)
            assert props == required, f"{path}: optional fields {sorted(props - required)}"
        for keyword in ("maxItems", "maxLength", "minimum", "maximum", "default"):
            assert keyword not in node, f"{path}: unsupported keyword {keyword}"
        if node.get("type") == "number":
            raise AssertionError(f"{path}: numbers in the reply must be integers")
    assert objects >= 8  # reply, policy, allocation, order, message, commitment, belief, name
    assert optional == 0 and optional <= ANTHROPIC_MAX_OPTIONAL
    assert union == 0 and union <= ANTHROPIC_MAX_UNION


def test_reply_schema_lists_every_adr_field():
    schema = _reply_schema()
    assert set(schema["required"]) == {
        "decision_id",
        "policy",
        "orders",
        "messages",
        "commitments",
        "beliefs",
        "names",
        "journal",
        "annal",
    }


def test_schema_export_is_current():
    rendered = render_schemas()
    assert set(rendered) == {REPLY_FILE, OBSERVATION_FILE}
    for name, text in rendered.items():
        assert text.endswith("\n") and not text.endswith("\n\n")
        parsed = json.loads(text)
        assert text == json.dumps(parsed, sort_keys=True, indent=2) + "\n", f"{name} not canonical"
        committed = (SCHEMA_DIR / name).read_text(encoding="utf-8")
        assert committed == text, f"schema/{name} is stale: run `just schema-export`"


def test_valid_reply_round_trips():
    reply = MindReply.model_validate(EXAMPLE_REPLY)
    assert reply.model_dump(mode="json") == EXAMPLE_REPLY
    again = MindReply.model_validate_json(reply.model_dump_json())
    assert again == reply


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda r: r.update(extra=1), id="unknown-top-level-field"),
        pytest.param(lambda r: r["orders"][0].update(priority=1), id="unknown-nested-field"),
        pytest.param(lambda r: r.pop("annal"), id="missing-field"),
        pytest.param(lambda r: r["policy"].pop("ration"), id="missing-nested-field"),
        pytest.param(lambda r: r["orders"][0].update(qty=2.0), id="float-qty"),
        pytest.param(lambda r: r["policy"].update(ration=999.5), id="float-ration"),
        pytest.param(lambda r: r["orders"][0].update(qty=True), id="bool-as-int"),
        pytest.param(lambda r: r["orders"][0].update(qty="2"), id="string-as-int"),
        pytest.param(lambda r: r.update(journal=None), id="null-text"),
    ],
)
def test_malformed_reply_rejected(mutate):
    bad = json.loads(json.dumps(EXAMPLE_REPLY))
    mutate(bad)
    with pytest.raises(ValidationError):
        MindReply.model_validate(bad)
    with pytest.raises(ValidationError):
        MindReply.model_validate_json(json.dumps(bad))


def test_observation_schema_is_closed_and_integer_only():
    schema = json.loads(render_schemas()[OBSERVATION_FILE])
    sections = {
        "calendar",
        "status",
        "places",
        "events",
        "messages",
        "standing",
        "last_results",
        "knowledge",
        "journal",
    }
    assert sections <= set(schema["properties"])
    for path, node in _walk(schema):
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False, path
            assert set(node.get("properties", {})) == set(node.get("required", [])), path
        assert node.get("type") != "number", f"{path}: observation numbers must be integers"
    assert Observation.model_config.get("extra") == "forbid"
