"""Hunger: eating, spoilage and death from a shortfall (backlog M0b).

Each tick, for each living tribe (any order: tribes do not interact here, so
each civ's result is independent of the others):

1. **Eat.** The tribe needs ``population * food_need * ration / 1000`` mu
   (``food_need`` per its period, ``ration`` in permille from the standing
   policy), through a carried remainder. It eats what the stores hold, up to
   that (``CONSUME``). Stores never go negative.
2. **Spoil.** ``store_spoilage`` of what is left rots (``SPOIL``), through a
   carried remainder.
3. **Starve.** If the tribe ate less than it needed, each person dies with
   probability ``starvation_death * shortfall / need``: the full death
   chance when nothing was eaten, none when the need was met. The chance is
   drawn per person from the LIFE stream, exactly as a fraction
   (``fixed.chance_fraction``), so a small shortfall still carries a small
   risk. Deaths are recorded as ``evidence`` at the camp. A ration below
   1000 lowers the need, so it is not a shortfall: rationing is a choice,
   starving is not.

No births in M0 (they come in M3). A tribe at population 0 is extinct and
every system leaves it alone.

Draws: one sub-key per tribe, ``draw(key(LIFE), civ entity id, n)`` with the
registered ``m0_starvation`` site, then ``draw(sub_key, person index)`` for
each person, so tribes never share numbers.
"""

from dataclasses import dataclass, field
from typing import Final

from aimpire.sim.calendar import Flow, Rate
from aimpire.sim.fixed import PPM, chance_fraction
from aimpire.sim.rng import SITES, draw
from aimpire.sim.scheduler import Cadence, TickContext
from aimpire.sim.state import Entity, WorldState
from aimpire.sim.systems.tribe import (
    CONSUME,
    SPOIL,
    add_evidence,
    camp,
    civ_id,
    flow,
    living_civ_ids,
    population,
    ration,
    stores_food,
    take_from_stores,
)

NAME: Final = "hunger"
_STREAM, _N = SITES["m0_starvation"]
_PPM_PER_PERMILLE: Final = 1000


@dataclass(frozen=True, slots=True)
class Hunger:
    """Eat, spoil, starve."""

    food_need: Flow
    """What one person eats on a full ration."""
    store_spoilage: Rate
    """Share of the stores that rots."""
    starvation_death: Rate
    """Chance that a person given nothing dies."""
    name: str = field(default=NAME, init=False)
    cadence: Cadence = field(default="tick", init=False)
    sequential: bool = field(default=False, init=False)

    def step(self, state: WorldState, ctx: TickContext) -> None:
        """One tick of eating, spoilage and starvation for every living tribe."""
        for eid in living_civ_ids(state):
            entity = state.entities[eid]
            need, eaten = self._eat(ctx, entity)
            self._spoil(ctx, entity)
            if eaten < need:
                self._starve(state, ctx, eid, need=need, shortfall=need - eaten)

    def _eat(self, ctx: TickContext, entity: Entity) -> tuple[int, int]:
        mu, per = self.food_need.resolve(ctx.calendar)
        ppm = ration(entity) * _PPM_PER_PERMILLE
        need = flow(entity, "need", population(entity) * mu, ppm, per)
        eaten = take_from_stores(entity, ctx.ledger, need, CONSUME, f"{civ_id(entity)}:eat")
        return need, eaten

    def _spoil(self, ctx: TickContext, entity: Entity) -> None:
        ppm, per = self.store_spoilage.resolve(ctx.calendar)
        rotten = flow(entity, "spoil", stores_food(entity), ppm, per)
        take_from_stores(entity, ctx.ledger, rotten, SPOIL, f"{civ_id(entity)}:spoil")

    def _starve(
        self, state: WorldState, ctx: TickContext, eid: int, *, need: int, shortfall: int
    ) -> None:
        """Each person dies with chance ``starvation_death * shortfall / need`` (mu over mu)."""
        entity = state.entities[eid]
        ppm, per = self.starvation_death.resolve(ctx.calendar)
        numer, denom = ppm * shortfall, PPM * per * need
        sub_key = draw(ctx.key(_STREAM), eid, _N)
        people = population(entity)
        deaths = sum(1 for i in range(people) if chance_fraction(draw(sub_key, i), numer, denom))
        if deaths:
            entity["population"] = people - deaths
            word = "person" if deaths == 1 else "people"
            add_evidence(state, entity, camp(entity), f"{deaths} {word} died of hunger.")
