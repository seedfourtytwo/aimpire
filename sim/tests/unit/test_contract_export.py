"""Unit tests for the schema exporter and the contract vocabulary."""

import json
from pathlib import Path

from aimpire.contracts.export import check_schemas, main, render_schemas, write_schemas
from aimpire.contracts.mind import MindReply
from aimpire.contracts.vocabulary import ACTIVITIES, ORDER_KINDS


def test_render_is_deterministic():
    assert render_schemas() == render_schemas()


def test_check_passes_on_fresh_export(tmp_path: Path):
    write_schemas(tmp_path)
    assert check_schemas(tmp_path) == []
    assert main(["--check", str(tmp_path)]) == 0


def test_check_reports_drift_and_missing(tmp_path: Path):
    paths = write_schemas(tmp_path)
    paths[0].write_text(paths[0].read_text(encoding="utf-8") + " ", encoding="utf-8")
    paths[1].unlink()
    problems = check_schemas(tmp_path)
    assert len(problems) == 2
    assert any(p.startswith("missing:") for p in problems)
    assert main(["--check", str(tmp_path)]) == 1


def test_kinds_are_listed_in_reply_schema_but_open_in_python():
    """The schema lists kinds so constrained decoding cannot invent one (Ollama sent
    "move" and "collect" without it); parsing stays open so an unconstrained
    provider's unknown kind is still rejected later as UNKNOWN_ACTION."""
    schema = MindReply.model_json_schema()
    order = schema["$defs"]["Order"]["properties"]["kind"]
    assert order["type"] == "string" and order["enum"] == sorted(ORDER_KINDS)
    assert all(kind in order["description"] for kind in ORDER_KINDS)


def test_activities_are_order_kinds():
    assert ACTIVITIES <= ORDER_KINDS


def test_exported_text_is_ascii_json():
    for text in render_schemas().values():
        json.loads(text)
        assert text.isascii()
