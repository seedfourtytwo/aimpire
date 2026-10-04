"""Ledger of conserved quantities and the per-system invariant check (F3).

Why: food, wood and every other material must never appear or vanish without
a recorded cause. Each system that changes a conserved quantity writes a ledger
entry ``(tick, system, material, delta, kind, ref)``. In checked mode the
scheduler measures every material before and after each system and fails if
the measured change differs from the recorded deltas. This catches leaks,
double counting and silent creation the moment they happen, in the system
that caused them.

Kinds name the cause of a change, for example ``REGROWTH``, ``HARVEST``,
``CONSUME``, ``SPOIL`` or ``TRADE``. A transfer between two materials or
places is two entries that sum to zero within each material.

The ledger is audit output, like the events table (ADR-0004); it is not part
of the state hash.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import numpy as np

from aimpire.sim.state import WorldState

Measure = Callable[[WorldState], int]


class InvariantError(AssertionError):
    """A system broke a simulation invariant."""


class UnrecordedChangeError(InvariantError):
    """A conserved quantity changed by a different amount than the ledger records."""


class NegativeStockError(InvariantError):
    """A tile layer, carry layer or measured quantity went below zero."""


@dataclass(frozen=True, slots=True)
class Entry:
    """One recorded change to a conserved quantity, in milli-units."""

    tick: int
    system: str
    material: str
    delta: int
    kind: str
    ref: str = ""


def _check_kind(kind: str) -> None:
    if not kind or not kind.replace("_", "").isalpha() or not kind.isupper():
        raise ValueError(f"kind must be an UPPER_CASE word such as 'HARVEST', got {kind!r}")


@dataclass(slots=True)
class Ledger:
    """Append-only list of ledger entries. Systems write through ``record``."""

    entries: list[Entry] = field(default_factory=list[Entry])
    _system: str = ""
    _tick: int = 0
    _start: int = 0

    def begin(self, system: str, tick: int) -> None:
        """Start a new system step: later entries belong to ``system`` at ``tick``."""
        self._system, self._tick, self._start = system, tick, len(self.entries)

    @property
    def current(self) -> list[Entry]:
        """Entries written since the last ``begin``."""
        return self.entries[self._start :]

    def record(self, material: str, delta: int, kind: str, ref: str = "") -> None:
        """Record a change of ``delta`` milli-units to ``material`` caused by ``kind``."""
        if type(delta) is not int:
            raise TypeError(f"delta must be an int, got {delta!r}")
        if not material:
            raise ValueError("material must be named")
        _check_kind(kind)
        self.entries.append(Entry(self._tick, self._system, material, delta, kind, ref))

    def net(self, material: str, *, current_only: bool = False) -> int:
        """Sum of deltas for ``material``: all entries, or only those since ``begin``."""
        entries = self.current if current_only else self.entries
        return sum(e.delta for e in entries if e.material == material)


def layer_total(name: str) -> Measure:
    """Measure: the sum of a tile layer, in milli-units."""

    def measure(state: WorldState) -> int:
        return int(state.layers[name].sum(dtype=np.int64))

    return measure


def entity_field_total(kind: str, path: tuple[str, ...]) -> Measure:
    """Measure: the sum of an int field (``path`` into each entity's dict) over one entity kind."""

    def measure(state: WorldState) -> int:
        total = 0
        for entity in state.entities.values():
            if entity.get("kind") != kind:
                continue
            value: object = entity
            for key in path:
                value = value.get(key, 0) if isinstance(value, dict) else 0  # pyright: ignore[reportUnknownMemberType]
            if type(value) is int:
                total += value
        return total

    return measure


def measure_all(state: WorldState, quantities: Mapping[str, Measure]) -> dict[str, int]:
    """Measure every conserved material."""
    return {name: measure(state) for name, measure in quantities.items()}


def check_after_system(
    state: WorldState,
    system: str,
    before: Mapping[str, int],
    quantities: Mapping[str, Measure],
    ledger: Ledger,
) -> dict[str, int]:
    """Verify one system's effect and return the new measurements.

    Fails if any layer or carry is negative, or if any material's measured
    change differs from the ledger entries the system wrote.
    """
    for name, grid in (*state.layers.items(), *state.carries.items()):
        if grid.size and int(grid.min()) < 0:
            raise NegativeStockError(f"{system} left layer {name!r} negative at tick {state.tick}")
    after = measure_all(state, quantities)
    for material, value in after.items():
        if value < 0:
            raise NegativeStockError(f"{system} left {material!r} at {value} at tick {state.tick}")
        recorded = ledger.net(material, current_only=True)
        actual = value - before[material]
        if actual != recorded:
            raise UnrecordedChangeError(
                f"{system} changed {material!r} by {actual} at tick {state.tick} "
                f"but recorded {recorded}"
            )
    unknown = {e.material for e in ledger.current} - set(quantities)
    if unknown:
        raise UnrecordedChangeError(f"{system} recorded unmeasured materials: {sorted(unknown)}")
    return after
