"""Scouting: dated snapshots of distant places, and discovery (backlog M0b).

What a scout does at a place: look at every place within ``scout.sight`` of
it (``survey``), write the snapshot into the tribe's ``known`` map with the
tick, and leave an ``evidence`` entity saying what was seen. Places seen for
the first time become known, so scouting is how the map is discovered. The
snapshot is never refreshed by anything but another look: the mind sees how
old its knowledge is, not live truth.

**Standing scouts.** ``k`` workers allocated to ``SCOUT`` at a place ``T``
walking ticks from camp complete ``k / (1 + 2T)`` round trips a tick
(a carried remainder, ``tribe.flow``). On a tick in which at least one trip
completes they report once. They burn walking energy like foragers do.

**Trips.** A ``SCOUT`` order sends ``qty`` people (1 to 4) once. On reaching
the place they look around and report; they burn walking energy every tick
on the road and are back at the trip's ``done`` tick.
"""

from dataclasses import dataclass, field
from typing import Final

from aimpire.sim.calendar import Flow
from aimpire.sim.fixed import PPM
from aimpire.sim.scheduler import Cadence, TickContext
from aimpire.sim.state import Entity, WorldState
from aimpire.sim.systems.survey import describe_seen, survey, walk_ticks
from aimpire.sim.systems.tribe import (
    CONSUME,
    add_evidence,
    camp,
    civ_id,
    flow,
    living_civ_ids,
    take_from_stores,
)
from aimpire.sim.systems.work import (
    DONE,
    EN_ROUTE,
    RETURNING,
    SCOUT,
    set_task,
    tasks,
    times_of,
    work_lines,
)

NAME: Final = "scout"


@dataclass(frozen=True, slots=True)
class Scout:
    """Standing scouts and ``SCOUT`` trips."""

    walk_energy: Flow
    """Extra food a walking person burns at Earth gravity."""
    walk_speed: int
    """W0 walking speed, ppm of Earth."""
    walk_energy_scale: int
    """W0 walking energy, ppm of Earth."""
    sight: int
    """Rules ``scout.sight``, tiles."""
    name: str = field(default=NAME, init=False)
    cadence: Cadence = field(default="tick", init=False)
    sequential: bool = field(default=True, init=False)

    def step(self, state: WorldState, ctx: TickContext) -> None:
        """Every living tribe's scouts, in the shuffled order."""
        for eid in ctx.order(living_civ_ids(state)):
            entity = state.entities[eid]
            for activity, place, workers in work_lines(entity):
                if activity == SCOUT and workers > 0:
                    self._standing(state, ctx, entity, place, workers)
            self._trips(state, ctx, entity)

    def _look(self, state: WorldState, entity: Entity, place: str) -> None:
        seen = survey(state, entity, place, self.sight)
        add_evidence(state, entity, place, f"Scouts at {place} saw: {describe_seen(seen)}.")

    def _standing(
        self, state: WorldState, ctx: TickContext, entity: Entity, place: str, workers: int
    ) -> None:
        walk = walk_ticks(state, camp(entity), place, self.walk_speed)
        trip = 1 + 2 * walk
        key = f"scout:{place}"
        if flow(entity, key, workers, PPM, trip) > 0:
            self._look(state, entity, place)
        if walk:
            mu, per = self.walk_energy.resolve(ctx.calendar)
            value = workers * mu * 2 * walk
            burned = flow(entity, f"walk:{key}", value, self.walk_energy_scale, per * trip)
            take_from_stores(entity, ctx.ledger, burned, CONSUME, f"{civ_id(entity)}:{place}:walk")

    def _trips(self, state: WorldState, ctx: TickContext, entity: Entity) -> None:
        walkers = 0
        for task in tasks(entity):
            if task.kind != SCOUT or task.status not in (EN_ROUTE, RETURNING):
                continue
            times = times_of(entity, task.task_id)
            if task.status == EN_ROUTE and state.tick >= times.arrive:
                self._look(state, entity, task.place)
                set_task(entity, task.task_id, RETURNING)
            elif task.status == RETURNING and state.tick >= times.done:
                set_task(entity, task.task_id, DONE)
                continue
            if times.arrive > times.start:
                walkers += task.qty
        if walkers:
            mu, per = self.walk_energy.resolve(ctx.calendar)
            burned = flow(entity, "walk:scout:trips", walkers * mu, self.walk_energy_scale, per)
            take_from_stores(entity, ctx.ledger, burned, CONSUME, f"{civ_id(entity)}:walk:scouts")
