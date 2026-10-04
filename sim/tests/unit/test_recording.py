"""Unit tests for recorded-result records and the JSON Lines format."""

from pathlib import Path

import pytest

from aimpire.cognition.protocol import NO_USAGE, CognitionResult, elapsed_ms, parse_reply
from aimpire.cognition.recording import (
    read_jsonl,
    result_from_record,
    result_to_record,
    write_jsonl,
)


def _result(raw: str, status: str = "schema_fail") -> CognitionResult:
    return CognitionResult(
        raw_text=raw,
        parsed=parse_reply(raw)[0],
        status=status,  # type: ignore[arg-type]
        usage=NO_USAGE,
        model_reported="m",
        latency_ms=1,
        attempts=1,
    )


def test_lone_surrogate_survives_the_file(tmp_path: Path):
    raw = '{"journal": "\ud800 broken"}'
    path = tmp_path / "r.jsonl"
    write_jsonl(path, {"D1": _result(raw)})
    assert path.read_bytes().isascii()
    assert result_from_record(read_jsonl(path)["D1"]).raw_text == raw


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("status", "maybe"),
        ("latency_ms", 1.5),
        ("attempts", True),
        ("raw_text", None),
    ],
)
def test_bad_records_are_refused(key: str, value: object):
    record = result_to_record(_result("{}"))
    record[key] = value
    with pytest.raises(ValueError):
        result_from_record(record)


def test_missing_field_is_refused():
    record = result_to_record(_result("{}"))
    del record["usage"]
    with pytest.raises(KeyError):
        result_from_record(record)


def test_duplicate_decision_ids_in_file_are_refused(tmp_path: Path):
    path = tmp_path / "r.jsonl"
    write_jsonl(path, {"D1": _result("{}")})
    line = path.read_text(encoding="ascii")
    path.write_text(line + line, encoding="ascii")
    with pytest.raises(ValueError, match="duplicate"):
        read_jsonl(path)


def test_non_reply_statuses_are_not_parsed():
    record = result_to_record(_result('{"a": 1}', status="truncated"))
    assert result_from_record(record).parsed is None


def test_elapsed_ms_rounds_up_in_integers():
    assert elapsed_ms(0, 1) == 1
    assert elapsed_ms(0, 1_000_000) == 1
    assert elapsed_ms(0, 1_000_001) == 2
    assert elapsed_ms(5, 0) == 0
    assert type(elapsed_ms(0, 3)) is int
