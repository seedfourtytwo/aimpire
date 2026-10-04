"""Ordered, preset-driven system scheduler (ADR-0010, ADR-0011, ADR-0012, ADR-0015).

Why: every milestone is a named preset, an ordered list of systems with
parameters. Earlier experiments stay reproducible because a preset pins
exactly which systems run, in which order, at which cadence. Nothing is
skipped silently: a preset that names an unknown system, or names one twice,
is an error.

One call to ``Scheduler.step`` advances the world one tick:
    1. every system runs, in preset order, if its cadence matches the current
       tick (``tick`` always; ``season`` and ``year`` on their first tick);
    2. ``state.tick`` increases by one.

Systems get randomness and turn order only through ``TickContext``, so all
draws are counter-based (ADR-0012). A sequential system acts on entities in
``ctx.order(ids)``, a fresh shuffle every tick; it never relies on id order.
"""

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

from aimpire.sim.calendar import Calendar
from aimpire.sim.rng import SITES, permutation, stream_key
from aimpire.sim.state import Value, WorldState

Cadence = Literal["tick", "season", "year"]
_CADENCES: frozenset[str] = frozenset({"tick", "season", "year"})

_ORDER_STREAM, _ORDER_N = SITES["turn_order"]


@dataclass(frozen=True, slots=True)
class TickContext:
    """What a system may use besides the state: the calendar and counter-based draws."""

    calendar: Calendar
    run_seed: int
    tick: int

    def key(self, stream: int) -> int:
        """The draw key for ``stream`` at this tick (pass to ``rng.draw``)."""
        return stream_key(self.run_seed, self.tick, stream)

    def order(self, ids: Iterable[int]) -> list[int]:
        """The acting order for a sequential system this tick: a fresh deterministic shuffle."""
        return permutation(self.key(_ORDER_STREAM), ids, _ORDER_N)


class System(Protocol):
    """One rule of the world. Pure: changes ``state`` and does nothing else."""

    @property
    def name(self) -> str: ...

    @property
    def cadence(self) -> Cadence: ...

    @property
    def sequential(self) -> bool: ...

    def step(self, state: WorldState, ctx: TickContext) -> None: ...


SystemFactory = Callable[[Mapping[str, Value]], System]


@dataclass(frozen=True, slots=True)
class SystemSpec:
    """One preset entry: a registered system name and its parameters."""

    name: str
    params: Mapping[str, Value] = field(default_factory=dict[str, Value])


@dataclass(frozen=True, slots=True)
class Preset:
    """A named, ordered list of systems: one per milestone (``m0``, ``m1``, ...)."""

    name: str
    systems: Sequence[SystemSpec]


class PresetError(ValueError):
    """A preset does not match the registered systems."""


def _due(cadence: Cadence, calendar: Calendar, tick: int) -> bool:
    if cadence == "tick":
        return True
    if cadence == "season":
        return calendar.is_season_start(tick)
    return calendar.is_year_start(tick)


class Scheduler:
    """Builds the systems a preset names and runs them tick by tick."""

    def __init__(
        self, preset: Preset, registry: Mapping[str, SystemFactory], calendar: Calendar
    ) -> None:
        names = [spec.name for spec in preset.systems]
        unknown = sorted(set(names) - set(registry))
        if unknown:
            raise PresetError(f"preset {preset.name!r} names unknown systems: {unknown}")
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise PresetError(f"preset {preset.name!r} names systems twice: {duplicates}")
        systems: list[System] = []
        for spec in preset.systems:
            system = registry[spec.name](spec.params)
            if system.name != spec.name:
                raise PresetError(f"factory for {spec.name!r} built a system named {system.name!r}")
            if system.cadence not in _CADENCES:
                raise PresetError(f"system {system.name!r} has unknown cadence {system.cadence!r}")
            systems.append(system)
        self.preset = preset
        self.calendar = calendar
        self.systems: tuple[System, ...] = tuple(systems)

    def step(self, state: WorldState) -> None:
        """Run every due system once, in preset order, then advance the tick."""
        ctx = TickContext(calendar=self.calendar, run_seed=state.run_seed, tick=state.tick)
        for system in self.systems:
            if _due(system.cadence, self.calendar, state.tick):
                system.step(state, ctx)
        state.tick += 1

    def run(self, state: WorldState, ticks: int) -> None:
        """Advance ``ticks`` ticks."""
        if ticks < 0:
            raise ValueError(f"ticks must be >= 0, got {ticks}")
        for _ in range(ticks):
            self.step(state)
