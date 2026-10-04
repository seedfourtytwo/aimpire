"""The frozen inputs of ``aimpire qualify``: observation cases and pass marks (backlog F6c).

Why frozen files: qualification compares models, and a comparison is only
fair on identical inputs. ``data/qualify-cases-v1.json`` holds m0
observations covering the situations a mind meets (first council, evidence
and a quoted message, low food, a rejected order, an open task, a named and an
unseen place). Each case also stores a scripted mock reply, so ``qualify
mock`` checks the qualifier itself against known rates: of the 6 replies, 3
parse; they propose 5 orders and 4 are valid.

``data/qualify-thresholds-v1.toml`` holds the pass marks. Changing a case or
a mark means a new file and version; reports name both versions and the
cases file's hash.
"""

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, cast, get_args

from aimpire.cognition.offline import MockFailure
from aimpire.cognition.protocol import Status
from aimpire.contracts.mind import Observation
from aimpire.experiments.experiment import file_hash

DATA: Final = Path(__file__).parent / "data"
DEFAULT_CASES: Final = DATA / "qualify-cases-v1.json"
DEFAULT_THRESHOLDS: Final = DATA / "qualify-thresholds-v1.toml"
_THRESHOLD_KEYS: Final = (
    "min_schema_adherence_ppm",
    "min_order_validity_ppm",
    "max_latency_p50_ms",
    "max_latency_max_ms",
)


@dataclass(frozen=True, slots=True)
class Case:
    """One frozen observation and the mock's scripted answer to it."""

    observation: Observation
    mock: str | MockFailure


@dataclass(frozen=True, slots=True)
class Cases:
    """The case set, its version and the BLAKE2b hash of the file it came from."""

    version: str
    file_hash: str
    cases: tuple[Case, ...]


@dataclass(frozen=True, slots=True)
class Thresholds:
    """Pass marks: rates in parts per million, latency in milliseconds."""

    version: str
    min_schema_adherence_ppm: int
    min_order_validity_ppm: int
    max_latency_p50_ms: int
    max_latency_max_ms: int


def _mock(entry: dict[str, Any]) -> str | MockFailure:
    """``{"reply": text}`` or ``{"failure": status, "raw_text": text}``."""
    if "reply" in entry:
        return str(entry["reply"])
    status = entry["failure"]
    if status not in get_args(Status):
        raise ValueError(f"unknown mock failure status {status!r}")
    return MockFailure(status=cast(Status, status), raw_text=str(entry.get("raw_text", "")))


def load_cases(path: Path = DEFAULT_CASES) -> Cases:
    """Read and validate a cases file. Decision ids must be unique across cases."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = tuple(
        Case(Observation.model_validate(c["observation"]), _mock(c["mock"])) for c in raw["cases"]
    )
    if not cases:
        raise ValueError(f"{path}: no cases")
    ids = [c.observation.decision_id for c in cases]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{path}: decision ids repeat")
    return Cases(version=str(raw["version"]), file_hash=file_hash(path), cases=cases)


def load_thresholds(path: Path = DEFAULT_THRESHOLDS) -> Thresholds:
    """Read a thresholds file; every mark is a required non-negative int."""
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    unknown = sorted(set(raw) - {"version", *_THRESHOLD_KEYS})
    if unknown:
        raise ValueError(f"{path}: unknown keys {unknown}")
    marks: dict[str, int] = {}
    for key in _THRESHOLD_KEYS:
        value = raw.get(key)
        if type(value) is not int or value < 0:
            raise ValueError(f"{path}: {key} must be a non-negative int, got {value!r}")
        marks[key] = value
    return Thresholds(version=str(raw["version"]), **marks)
