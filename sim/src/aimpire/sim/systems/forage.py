"""Foraging: wild food from a place's tiles into the tribe's stores (backlog M0b).

**Standing foragers.** ``n`` workers allocated to ``FORAGE`` at a place
``T`` walking ticks from camp make round trips of ``1 + 2T`` ticks (out,
gather, back) and bring ``carry`` mu each, so together they gather

    n * carry_per_trip * carry_load / (PPM * (1 + 2T))   mu a tick,

with ``carry_load`` the W0 rate (ppm of Earth: ∝ 1/g), through a carried
remainder (``tribe.flow``). They walk ``2T`` of every ``1 + 2T`` ticks, so
they also burn

    n * walk_energy * walk_energy_scale * 2T / (PPM * per * (1 + 2T))   mu a tick,

eaten from the stores after the harvest is in (``CONSUME``). ``T`` is the true
``walk_ticks`` (``survey`` module: travel at the W0 walking speed).

**Trips.** A ``FORAGE`` order sends ``qty`` people once. When they reach the
place each takes one full carry (``qty * carry_per_trip * carry_load / PPM``);
the food is counted into the stores at once. They burn walking energy every
tick they are on the road, and are back at the trip's ``done`` tick.

**Taking from tiles.** A harvest is capped by the food on the place's tiles
and spread over them in proportion to the food each holds: tile ``i`` gives
``floor(h * F_i / F)``, and the few mu of rounding left go one each to the
first tiles in sorted (row-major) order whose share was rounded down. Every
tile so loses the same fraction of its food, and a place harvested this way
regrows as one logistic unit with ceiling ``sum(K_i)``: that is what makes
its steady yield peak near half full (M0a). Taking tiles one by one down to
zero, the M0b order, left stripped tiles to regrow from the seed term alone,
so no place could yield more than about 2 units a tick (M0c calibration).
One ``HARVEST`` pair per harvest: ``-h`` of ``food`` (the tile layer) and
``+h`` of ``stores``.

Sequential: tribes act in the per-tick shuffled order, so when two forage
the same place the order of first pick is fair over time (ADR-0012 C).
"""

from dataclasses import dataclass, field
from typing import Final

import numpy as np

from aimpire.sim.calendar import Flow
from aimpire.sim.ledger import Ledger
from aimpire.sim.places import Place, places_by_id
from aimpire.sim.scheduler import Cadence, TickContext
from aimpire.sim.state import Entity, WorldState
from aimpire.sim.systems.regrowth import MATERIAL as FOOD_MATERIAL
from aimpire.sim.systems.survey import walk_ticks
from aimpire.sim.systems.tribe import (
    CONSUME,
    HARVEST,
    add_to_stores,
    camp,
    civ_id,
    flow,
    living_civ_ids,
    take_from_stores,
)
from aimpire.sim.systems.work import (
    DONE,
    EN_ROUTE,
    FORAGE,
    RETURNING,
    set_task,
    tasks,
    times_of,
    work_lines,
)
from aimpire.sim.world.m0 import FOOD as FOOD_LAYER

NAME: Final = "forage"
_ROW: Final = 0
_COL: Final = 1


def take_food(state: WorldState, place: Place, wanted: int) -> int:
    """Remove up to ``wanted`` mu from ``place``'s tiles in proportion to their food; return it.

    See the module docstring. Integer only: each tile's share is floored and
    the remainder (fewer mu than there are tiles) goes one mu each to the
    first tiles in sorted order whose share was rounded down, so no tile goes
    below zero and the total taken is exactly ``min(wanted, food)``.
    """
    if wanted <= 0 or not place.tiles:
        return 0
    tiles = sorted(place.tiles)
    rows = np.fromiter((t[_ROW] for t in tiles), dtype=np.int64, count=len(tiles))
    cols = np.fromiter((t[_COL] for t in tiles), dtype=np.int64, count=len(tiles))
    layer = state.layers[FOOD_LAYER]
    food = layer[rows, cols]
    total = int(food.sum(dtype=np.int64))
    if total == 0:
        return 0
    if wanted >= total:
        layer[rows, cols] = 0
        return total
    # Proportional share of one harvest (not a rate over time), floored per tile.
    numer = food * np.int64(wanted)
    take = numer // np.int64(total)
    rounded_down = np.flatnonzero(numer % np.int64(total))
    take[rounded_down[: wanted - int(take.sum(dtype=np.int64))]] += 1
    layer[rows, cols] = food - take
    return wanted


def record_harvest(ledger: Ledger, entity: Entity, taken: int, ref: str) -> None:
    """The two sides of a harvest: tiles down, stores up."""
    if taken:
        ledger.record(FOOD_MATERIAL, -taken, HARVEST, ref)
        add_to_stores(entity, ledger, taken, HARVEST, ref)


@dataclass(frozen=True, slots=True)
class Forage:
    """Standing foragers and ``FORAGE`` trips."""

    carry_per_trip: int
    """Food one forager brings back per trip at Earth gravity, mu."""
    walk_energy: Flow
    """Extra food a walking person burns at Earth gravity."""
    carry_load: int
    """W0 carry load, ppm of Earth."""
    walk_speed: int
    """W0 walking speed, ppm of Earth."""
    walk_energy_scale: int
    """W0 walking energy, ppm of Earth."""
    name: str = field(default=NAME, init=False)
    cadence: Cadence = field(default="tick", init=False)
    sequential: bool = field(default=True, init=False)

    def step(self, state: WorldState, ctx: TickContext) -> None:
        """Every living tribe's foragers, in the shuffled order."""
        living = living_civ_ids(state)
        if not living:
            return
        places = places_by_id(state)
        for eid in ctx.order(living):
            entity = state.entities[eid]
            for activity, place, workers in work_lines(entity):
                if activity == FORAGE and workers > 0:
                    self._standing(state, ctx, entity, places[place], workers)
            self._trips(state, ctx, entity, places)

    def _standing(
        self, state: WorldState, ctx: TickContext, entity: Entity, place: Place, workers: int
    ) -> None:
        walk = walk_ticks(state, camp(entity), place.place_id, self.walk_speed)
        trip = 1 + 2 * walk
        key = f"forage:{place.place_id}"
        gathered = flow(entity, key, workers * self.carry_per_trip, self.carry_load, trip)
        ref = f"{civ_id(entity)}:{place.place_id}"
        record_harvest(ctx.ledger, entity, take_food(state, place, gathered), ref)
        if walk:
            mu, per = self.walk_energy.resolve(ctx.calendar)
            value = workers * mu * 2 * walk
            burned = flow(entity, f"walk:{key}", value, self.walk_energy_scale, per * trip)
            take_from_stores(entity, ctx.ledger, burned, CONSUME, f"{ref}:walk")

    def _trips(
        self, state: WorldState, ctx: TickContext, entity: Entity, places: dict[str, Place]
    ) -> None:
        walkers = 0
        for task in tasks(entity):
            if task.kind != FORAGE or task.status not in (EN_ROUTE, RETURNING):
                continue
            times = times_of(entity, task.task_id)
            if task.status == EN_ROUTE and state.tick >= times.arrive:
                wanted = flow(
                    entity, "forage:trips", task.qty * self.carry_per_trip, self.carry_load, 1
                )
                taken = take_food(state, places[task.place], wanted)
                record_harvest(ctx.ledger, entity, taken, f"{civ_id(entity)}:{task.task_id}")
                set_task(entity, task.task_id, RETURNING)
            elif task.status == RETURNING and state.tick >= times.done:
                set_task(entity, task.task_id, DONE)
                continue
            if times.arrive > times.start:  # a trip on the camp's own place walks nowhere
                walkers += task.qty
        if walkers:
            mu, per = self.walk_energy.resolve(ctx.calendar)
            burned = flow(entity, "walk:forage:trips", walkers * mu, self.walk_energy_scale, per)
            take_from_stores(entity, ctx.ledger, burned, CONSUME, f"{civ_id(entity)}:walk:trips")
