"""Recorded provider results: plain records and a JSON Lines file format (ADR-0004).

A record stores what is needed to give back the same ``CognitionResult``:
the raw text exactly as received, the status, usage, the reported model,
latency and attempts. ``parsed`` is not stored; it is derived again from the
raw text by the same ``parse_reply`` used live, so the two can never disagree.

File format: one JSON object per line, keys sorted, ``ensure_ascii=True``.
ASCII escapes make the raw text survive any file encoding, including lone
surrogates a model might emit, and decode to the identical string.

The run store (F5e) will keep these records in SQLite and blobs; this module is
the format both share.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final, cast

from aimpire.cognition.protocol import (
    STATUSES,
    CognitionResult,
    Status,
    Usage,
    parse_reply,
)

# Statuses whose raw text is a complete reply worth parsing.
_PARSED_STATUSES: Final = frozenset({"ok", "schema_fail"})
_USAGE_KEYS: Final = ("input_tokens", "output_tokens", "reasoning_tokens")


def result_to_record(result: CognitionResult) -> dict[str, Any]:
    """Return a JSON-ready record of ``result`` (everything except ``parsed``)."""
    return {
        "raw_text": result.raw_text,
        "status": result.status,
        "usage": {key: getattr(result.usage, key) for key in _USAGE_KEYS},
        "model_reported": result.model_reported,
        "latency_ms": result.latency_ms,
        "attempts": result.attempts,
    }


def _int(record: Mapping[str, Any], key: str) -> int:
    value = record[key]
    if type(value) is not int:
        raise ValueError(f"record field {key!r} must be an int, got {value!r}")
    return value


def _str(record: Mapping[str, Any], key: str) -> str:
    value = record[key]
    if not isinstance(value, str):
        raise ValueError(f"record field {key!r} must be a string")
    return value


def result_from_record(record: Mapping[str, Any]) -> CognitionResult:
    """Rebuild a result from a record. Raises ``KeyError``/``ValueError`` on a bad record."""
    status = _str(record, "status")
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}")
    raw_text = _str(record, "raw_text")
    usage = cast(Mapping[str, Any], record["usage"])
    parsed = parse_reply(raw_text)[0] if status in _PARSED_STATUSES else None
    return CognitionResult(
        raw_text=raw_text,
        parsed=parsed,
        status=cast(Status, status),
        usage=Usage(**{key: _int(usage, key) for key in _USAGE_KEYS}),
        model_reported=_str(record, "model_reported"),
        latency_ms=_int(record, "latency_ms"),
        attempts=_int(record, "attempts"),
    )


def write_jsonl(path: Path, results: Mapping[str, CognitionResult]) -> None:
    """Write ``{decision_id: result}`` as JSON Lines, in sorted decision-id order."""
    lines = [
        json.dumps(
            {"decision_id": decision_id, **result_to_record(results[decision_id])},
            sort_keys=True,
            ensure_ascii=True,
        )
        for decision_id in sorted(results)
    ]
    path.write_text("".join(line + "\n" for line in lines), encoding="ascii", newline="\n")


def read_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    """Read records written by ``write_jsonl``. Duplicate decision ids are an error."""
    records: dict[str, dict[str, Any]] = {}
    for number, line in enumerate(path.read_text(encoding="ascii").splitlines(), start=1):
        if not line:
            continue
        record = cast(dict[str, Any], json.loads(line))
        decision_id = record.pop("decision_id")
        if not isinstance(decision_id, str) or decision_id in records:
            raise ValueError(f"{path}:{number}: missing or duplicate decision_id")
        records[decision_id] = record
    return records
