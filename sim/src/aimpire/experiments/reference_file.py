"""The reference file: what a reference ensemble runs (backlog M0d, ADR-0014 section 1).

    kind: reference                 # tells ``aimpire batch`` this is not an experiment
    id: m0-reference
    purpose: "..."                  # what the bands are for
    world: m0                       # a registered world that records measures
    ticks: 600                      # five 120-day years
    council_every: 10
    checkpoint_every: 120           # a band point at every year boundary
    seeds: {first: 1, count: 200}   # or an explicit list
    minds: [rule:random, rule:greedy, rule:half_full, rule:msy]

Unknown keys are refused, as in an experiment file, so a typo cannot drop
part of the design. Only rule minds are accepted (``experiments.reference``
explains why), so a reference never spends anything.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, cast

import yaml

from aimpire.cognition.minds import MindError, MindSpec, resolve_mind
from aimpire.experiments.experiment import ExperimentError, file_hash
from aimpire.experiments.measures import has_measures
from aimpire.experiments.worlds import world_names

KIND: Final = "reference"
_TOP: Final = frozenset(
    {"kind", "id", "purpose", "world", "ticks", "council_every", "checkpoint_every"}
    | {"seeds", "minds"}
)


@dataclass(frozen=True, slots=True)
class ReferenceSpec:
    """A validated reference file. Times are in ticks (days)."""

    id: str
    file_hash: str
    purpose: str
    world: str
    ticks: int
    council_every: int
    checkpoint_every: int
    seeds: tuple[int, ...]
    minds: tuple[MindSpec, ...]


def is_reference(path: Path) -> bool:
    """Whether ``path`` is a reference file (``kind: reference``), not an experiment."""
    try:
        raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return False
    return isinstance(raw, dict) and cast(dict[str, Any], raw).get("kind") == KIND


def _int(raw: dict[str, Any], key: str) -> int:
    value = raw[key]
    if type(value) is not int or value < 1:
        raise ExperimentError(f"{key} must be an int >= 1, got {value!r}")
    return value


def _seeds(value: object) -> tuple[int, ...]:
    if isinstance(value, dict):
        table = cast(dict[str, Any], value)
        first, count = table.get("first"), table.get("count")
        if set(table) != {"first", "count"} or type(first) is not int or type(count) is not int:
            raise ExperimentError("seeds as a range must be {first: int, count: int}")
        if first < 0 or count < 1:
            raise ExperimentError("seeds: first must be >= 0 and count >= 1")
        return tuple(range(first, first + count))
    seeds = cast(list[Any], value) if isinstance(value, list) else []
    if (
        not seeds
        or any(type(s) is not int or s < 0 for s in seeds)
        or len(set(seeds)) != len(seeds)
    ):
        raise ExperimentError("seeds must be {first, count} or a list of distinct ints >= 0")
    return tuple(seeds)


def _minds(value: object, base_dir: Path) -> tuple[MindSpec, ...]:
    names = cast(list[Any], value) if isinstance(value, list) else []
    if not names:
        raise ExperimentError("minds must be a non-empty list")
    try:
        minds = tuple(resolve_mind(str(n), base_dir) for n in names)
    except MindError as exc:
        raise ExperimentError(f"minds: {exc}") from None
    if any(m.kind != "rule" for m in minds):
        raise ExperimentError("a reference runs rule minds only (they need no replicates)")
    if len({m.label for m in minds}) != len(minds):
        raise ExperimentError("minds repeats a mind")
    return minds


def load_reference(path: Path) -> ReferenceSpec:
    """Read and validate a reference file. Raises ``ExperimentError`` naming the problem."""
    try:
        raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ExperimentError(f"{path}: not valid YAML ({exc})") from None
    if not isinstance(raw, dict):
        raise ExperimentError(f"{path} must be a mapping")
    table = cast(dict[str, Any], raw)
    if missing := sorted(_TOP - set(table)):
        raise ExperimentError(f"{path}: missing {missing}")
    if unknown := sorted(set(table) - _TOP):
        raise ExperimentError(f"{path}: unknown keys {unknown}")
    if table["kind"] != KIND:
        raise ExperimentError(f"kind must be {KIND!r}")
    world = table["world"]
    if world not in world_names() or not has_measures(str(world)):
        raise ExperimentError(f"world must be a registered world with measures, got {world!r}")
    purpose = table["purpose"]
    if not isinstance(purpose, str) or not purpose.strip():
        raise ExperimentError("purpose must be a non-empty string")
    return ReferenceSpec(
        id=str(table["id"]),
        file_hash=file_hash(path),
        purpose=purpose.strip(),
        world=str(world),
        ticks=_int(table, "ticks"),
        council_every=_int(table, "council_every"),
        checkpoint_every=_int(table, "checkpoint_every"),
        seeds=_seeds(table["seeds"]),
        minds=_minds(table["minds"], path.parent),
    )
