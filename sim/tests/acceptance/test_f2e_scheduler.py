"""F2e acceptance: the preset-driven scheduler (ADR-0011, ADR-0012, ADR-0015).

Written by the planning model before implementation (ADR-0016). Read-only.
The systems below are test doubles, not simulation rules.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np
import pytest

from aimpire.sim.calendar import Calendar
from aimpire.sim.hashing import state_hash
from aimpire.sim.rng import Stream, draw, uniform_int
from aimpire.sim.scheduler import (
    Cadence,
    Preset,
    PresetError,
    Scheduler,
    SystemFactory,
    SystemSpec,
    TickContext,
)
from aimpire.sim.state import Value, WorldState

pytestmark = pytest.mark.acceptance

CAL = Calendar(ticks_per_season=30, seasons_per_year=4)


@dataclass
class Recorder:
    """Records the ticks it ran on and, if sequential, the acting order it was given."""

    name: str
    cadence: Cadence
    sequential: bool = False
    ticks: list[int] = field(default_factory=list[int])
    orders: list[list[int]] = field(default_factory=list[list[int]])

    def step(self, state: WorldState, ctx: TickContext) -> None:
        self.ticks.append(ctx.tick)
        if self.sequential:
            self.orders.append(ctx.order(sorted(state.entities)))


@dataclass
class Noise:
    """Adds a counter draw to every tile: makes the hash depend on the seed."""

    name: str = "noise"
    cadence: Cadence = "tick"
    sequential: bool = False

    def step(self, state: WorldState, ctx: TickContext) -> None:
        key = ctx.key(Stream.GROWTH)
        grid = state.layers["food"]
        for i in range(grid.size):
            grid.flat[i] += uniform_int(draw(key, i), 10)


def _world(seed: int, people: int = 0) -> WorldState:
    s = WorldState(run_seed=seed, rules_version="v1", rules_hash="test")
    s.add_layer("food", np.zeros((4, 4), dtype=np.int64))
    for _ in range(people):
        s.add_entity("person", {})
    return s


def _registry(*systems: object) -> dict[str, SystemFactory]:
    def factory(system: object) -> SystemFactory:
        def build(params: Mapping[str, Value]) -> object:
            assert not params
            return system

        return build  # type: ignore[return-value]

    return {s.name: factory(s) for s in systems}  # type: ignore[attr-defined]


def _preset(*names: str) -> Preset:
    return Preset(name="test", systems=[SystemSpec(n) for n in names])


def test_empty_world_same_hash_after_360_ticks() -> None:
    hashes = []
    for _ in range(2):
        state = _world(seed=1)
        Scheduler(_preset(), {}, CAL).run(state, 360)
        assert state.tick == 360
        hashes.append(state_hash(state))
    assert hashes[0] == hashes[1]

    def noisy(seed: int) -> str:
        state = _world(seed)
        Scheduler(_preset("noise"), _registry(Noise()), CAL).run(state, 360)
        return state_hash(state)

    assert noisy(1) == noisy(1)
    assert noisy(1) != noisy(2)


def test_cadence_runs_on_boundaries() -> None:
    daily, seasonal, yearly = Recorder("d", "tick"), Recorder("s", "season"), Recorder("y", "year")
    scheduler = Scheduler(_preset("d", "s", "y"), _registry(daily, seasonal, yearly), CAL)
    scheduler.run(_world(seed=3), 250)
    assert daily.ticks == list(range(250))
    assert seasonal.ticks == [0, 30, 60, 90, 120, 150, 180, 210, 240]
    assert yearly.ticks == [0, 120, 240]


def test_systems_run_in_preset_order() -> None:
    log: list[str] = []

    @dataclass
    class Named:
        name: str
        cadence: Cadence = "tick"
        sequential: bool = False

        def step(self, state: WorldState, ctx: TickContext) -> None:
            log.append(self.name)

    systems = (Named("a"), Named("b"), Named("c"))
    Scheduler(_preset("c", "a", "b"), _registry(*systems), CAL).run(_world(seed=1), 2)
    assert log == ["c", "a", "b", "c", "a", "b"]


def test_preset_mismatch_raises() -> None:
    registry = _registry(Recorder("d", "tick"))
    with pytest.raises(PresetError):
        Scheduler(_preset("d", "missing"), registry, CAL)  # unknown system: never a silent skip
    with pytest.raises(PresetError):
        Scheduler(_preset("d", "d"), registry, CAL)  # the same system twice
    with pytest.raises(PresetError):
        Scheduler(_preset("x"), {"x": _registry(Recorder("d", "tick"))["d"]}, CAL)  # name mismatch
    with pytest.raises(PresetError):
        Scheduler(_preset("w"), _registry(Recorder("w", "week")), CAL)  # type: ignore[arg-type]


def test_sequential_order_changes_each_tick_and_replays() -> None:
    def run() -> list[list[int]]:
        seq = Recorder("seq", "tick", sequential=True)
        Scheduler(_preset("seq"), _registry(seq), CAL).run(_world(seed=9, people=12), 20)
        return seq.orders

    first, second = run(), run()
    assert first == second  # replays exactly
    assert all(sorted(order) == list(range(1, 13)) for order in first)  # complete
    assert len({tuple(order) for order in first}) == 20  # a fresh order every tick
    assert sum(order[0] == 1 for order in first) < 20  # the oldest id does not always go first


def test_negative_run_rejected() -> None:
    with pytest.raises(ValueError):
        Scheduler(_preset(), {}, CAL).run(_world(seed=1), -1)
