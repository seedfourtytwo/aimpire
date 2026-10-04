"""F3 acceptance: every change to a conserved quantity is recorded and checked.

Written by the planning model before implementation (ADR-0016). Read-only.
The systems below are test doubles, not simulation rules.
"""

from dataclasses import dataclass

import numpy as np
import pytest

from aimpire.sim.calendar import Calendar
from aimpire.sim.fixed import apply_rate_array
from aimpire.sim.ledger import (
    Ledger,
    NegativeStockError,
    UnrecordedChangeError,
    entity_field_total,
    layer_total,
)
from aimpire.sim.scheduler import Cadence, Preset, Scheduler, SystemSpec, TickContext
from aimpire.sim.state import WorldState

pytestmark = pytest.mark.acceptance

CAL = Calendar(ticks_per_season=30, seasons_per_year=4)
QUANTITIES = {
    "food_on_land": layer_total("food"),
    "food_carried": entity_field_total("person", ("carry", "food")),
}


def _world() -> WorldState:
    s = WorldState(run_seed=5, rules_version="v1", rules_hash="test")
    s.add_layer("food", np.full((3, 3), 10_000, dtype=np.int64))
    for _ in range(3):
        s.add_entity("person", {"carry": {"food": 0}})
    return s


@dataclass
class Regrow:
    """Food regrows 2% per season on every tile, with carried remainders."""

    name: str = "regrow"
    cadence: Cadence = "tick"
    sequential: bool = False

    def step(self, state: WorldState, ctx: TickContext) -> None:
        deltas, state.carries["food"] = apply_rate_array(
            state.layers["food"], 20_000, ctx.calendar.ticks_per_season, state.carries["food"]
        )
        state.layers["food"] += deltas
        ctx.ledger.record("food_on_land", int(deltas.sum()), "REGROWTH")


@dataclass
class Harvest:
    """Each person takes 100 from tile (0, 0): a transfer recorded on both sides."""

    name: str = "harvest"
    cadence: Cadence = "tick"
    sequential: bool = True
    leak: int = 0
    record: bool = True

    def step(self, state: WorldState, ctx: TickContext) -> None:
        for pid in ctx.order(sorted(state.entities)):
            take = min(100, int(state.layers["food"][0, 0]))
            state.layers["food"][0, 0] -= take
            carry = state.entities[pid]["carry"]
            assert isinstance(carry, dict)
            food = carry["food"]
            assert isinstance(food, int)
            carry["food"] = food + take - self.leak
            if self.record:
                ctx.ledger.record("food_on_land", -take, "HARVEST", ref=f"P{pid}")
                ctx.ledger.record("food_carried", take, "HARVEST", ref=f"P{pid}")


def _scheduler(*systems: object) -> Scheduler:
    registry = {s.name: (lambda _p, s=s: s) for s in systems}  # type: ignore[attr-defined]
    preset = Preset("test", [SystemSpec(s.name) for s in systems])  # type: ignore[attr-defined]
    return Scheduler(preset, registry, CAL, quantities=QUANTITIES)  # type: ignore[arg-type]


def test_ledger_balances_toy_system() -> None:
    state, scheduler = _world(), _scheduler(Regrow(), Harvest())
    start = {name: measure(state) for name, measure in QUANTITIES.items()}
    scheduler.run(state, 240)  # raises if any system's change is unrecorded
    for name, measure in QUANTITIES.items():
        assert measure(state) - start[name] == scheduler.ledger.net(name)
    kinds = {e.kind for e in scheduler.ledger.entries}
    assert kinds == {"REGROWTH", "HARVEST"}
    assert {e.system for e in scheduler.ledger.entries} == {"regrow", "harvest"}


def test_unrecorded_change_detected() -> None:
    with pytest.raises(UnrecordedChangeError, match="harvest"):
        _scheduler(Harvest(record=False)).run(_world(), 1)
    with pytest.raises(UnrecordedChangeError, match="food_carried"):
        _scheduler(Harvest(leak=1)).run(_world(), 1)  # one milli-unit vanishes per person


def test_negative_stock_raises() -> None:
    @dataclass
    class Overdraw:
        name: str = "overdraw"
        cadence: Cadence = "tick"
        sequential: bool = False

        def step(self, state: WorldState, ctx: TickContext) -> None:
            state.layers["food"][1, 1] -= 20_000
            ctx.ledger.record("food_on_land", -20_000, "CONSUME")

    with pytest.raises(NegativeStockError, match="overdraw"):
        _scheduler(Overdraw()).run(_world(), 1)


def test_carry_included_in_balance() -> None:
    """A rate below one unit per tick still accrues: the ledger total matches the exact rate."""
    state, scheduler = _world(), _scheduler(Regrow())
    state.layers["food"][:] = 1_000
    scheduler.run(state, 30)  # one season at 2% per season, no harvest
    # 2% of 1,000 per tile per season = 20 per tile, 9 tiles; compounding adds a little.
    gained = scheduler.ledger.net("food_on_land")
    assert gained >= 180
    assert gained == int(state.layers["food"].sum()) - 9_000
    assert int(state.carries["food"].max()) < 1_000_000 * CAL.ticks_per_season


def test_unmeasured_material_rejected() -> None:
    @dataclass
    class Mystery:
        name: str = "mystery"
        cadence: Cadence = "tick"
        sequential: bool = False

        def step(self, state: WorldState, ctx: TickContext) -> None:
            ctx.ledger.record("gold", 5, "TRADE")

    with pytest.raises(UnrecordedChangeError, match="gold"):
        _scheduler(Mystery()).run(_world(), 1)


def test_ledger_rejects_bad_entries() -> None:
    ledger = Ledger()
    with pytest.raises(TypeError):
        ledger.record("food", 1.5, "HARVEST")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ledger.record("food", 1, "harvest")
    with pytest.raises(ValueError):
        ledger.record("", 1, "HARVEST")
