"""The camp system: moves, trip departures and today's work split (backlog M0b).

Runs first among the tribe systems each tick, so forage and scout see one
consistent picture of who is where. For each living tribe, in the per-tick
shuffled order (ADR-0012 section C):

1. **Move.** A ``MOVE_CAMP`` task that is ordered starts once no trip is
   ordered or out (``work`` module docstring). The whole tribe walks
   ``walk_ticks(camp, place)`` ticks; each tick on the way every person burns
   the walking energy (rules ``forage.walk_energy`` per its period, scaled
   by W0 ``walk_energy``), eaten from the stores (``CONSUME``). On arrival the camp is the
   new place, the people look around (a dated snapshot of the places in
   sight, ``survey``), and an ``evidence`` entity records the arrival.
2. **Trips.** Ordered ``FORAGE`` and ``SCOUT`` trips leave, unless the tribe is
   moving, with at most the people free; none free means ``FAILED``.
3. **Work split.** The free workers (everyone not on a trip; nobody while
   moving) are split by the standing policy (``work.apportion``) and stored
   in the civ's ``work`` field for forage and scout.

Units: food in mu, people as counts, ticks as game days.
"""

from dataclasses import dataclass, field
from typing import Final

from aimpire.sim.calendar import Flow
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
    policy_lines,
    population,
    take_from_stores,
)
from aimpire.sim.systems.work import DONE as TASK_DONE
from aimpire.sim.systems.work import (
    EN_ROUTE,
    FAILED,
    MOVE_CAMP,
    ORDERED,
    RETURNING,
    TRIP_KINDS,
    Task,
    TripTimes,
    apportion,
    is_moving,
    people_away,
    set_task,
    set_times,
    set_work,
    tasks,
    times_of,
    trip_times,
)

NAME: Final = "camp"
_WALK_CARRY: Final = "walk:move"


@dataclass(frozen=True, slots=True)
class Camp:
    """Moves the camp, sends trips out, and splits the free workers by the policy."""

    walk_energy: Flow
    """Extra food a walking person burns at Earth gravity (rules ``forage.walk_energy``)."""
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
        """One tick for every living tribe, in the shuffled order."""
        for eid in ctx.order(living_civ_ids(state)):
            entity = state.entities[eid]
            self._move(state, ctx, entity)
            moving = is_moving(entity)
            if not moving:
                self._start_trips(state, entity)
            free = 0 if moving else max(0, population(entity) - people_away(entity))
            set_work(entity, apportion(free, policy_lines(entity)))

    def _move(self, state: WorldState, ctx: TickContext, entity: Entity) -> None:
        en_route = [t for t in tasks(entity) if t.kind == MOVE_CAMP and t.status == EN_ROUTE]
        if not en_route:
            ordered = [t for t in tasks(entity) if t.kind == MOVE_CAMP and t.status == ORDERED]
            if not ordered or people_away(entity) > 0:
                return
            move = ordered[0]
            walk = walk_ticks(state, camp(entity), move.place, self.walk_speed)
            set_times(
                entity, move.task_id, TripTimes(state.tick, state.tick + walk, state.tick + walk)
            )
            set_task(entity, move.task_id, EN_ROUTE)
            en_route = [move]
        move = en_route[0]
        if state.tick >= times_of(entity, move.task_id).arrive:
            self._arrive(state, entity, move)
            return
        mu, per = self.walk_energy.resolve(ctx.calendar)
        burned = flow(entity, _WALK_CARRY, population(entity) * mu, self.walk_energy_scale, per)
        take_from_stores(entity, ctx.ledger, burned, CONSUME, f"{civ_id(entity)}:walk:move")

    def _arrive(self, state: WorldState, entity: Entity, move: Task) -> None:
        entity["camp"] = move.place
        seen = survey(state, entity, move.place, self.sight)
        add_evidence(
            state,
            entity,
            move.place,
            f"The camp moved to {move.place}. Seen: {describe_seen(seen)}.",
        )
        set_task(entity, move.task_id, TASK_DONE)

    def _start_trips(self, state: WorldState, entity: Entity) -> None:
        out = sum(
            t.qty
            for t in tasks(entity)
            if t.kind in TRIP_KINDS and t.status in (EN_ROUTE, RETURNING)
        )
        free = max(0, population(entity) - out)
        for task in tasks(entity):
            if task.kind not in TRIP_KINDS or task.status != ORDERED:
                continue
            people = min(task.qty, free)
            if people == 0:
                set_task(entity, task.task_id, FAILED)
                continue
            walk = walk_ticks(state, camp(entity), task.place, self.walk_speed)
            set_times(entity, task.task_id, trip_times(state.tick, walk))
            set_task(entity, task.task_id, EN_ROUTE, qty=people)
            free -= people
