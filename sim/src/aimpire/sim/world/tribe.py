"""Place the M0 tribe on a petri dish world (backlog M0b).

``place_tribe`` adds one ``civ`` entity in the layout ``cognition.civ_record``
reads, at tick 0:

* **Camp.** A place drawn from the seed: ``draw(key(WORLDGEN, tick 0), seat,
  n)`` with the registered ``m0_camp`` site, reduced to an index into the
  sorted place ids. The same seed always gives the same camp, and each seat
  draws its own.
* **People and stores.** ``rules.start_people`` as a count and
  ``{"food": rules.start_stores}`` mu.
* **Knowledge.** The people look around their camp: a dated snapshot (tick 0)
  of every place within ``rules.scout_sight`` (the camp and its neighbours on
  the default map), via ``survey``. Nothing else is known.
* **Policy.** No allocations and a full ration (1000‰). Nobody works until a
  mind sets a policy: the engine suggests no strategy (ADR-0019).
* **Bookkeeping.** Empty tasks, commitments and last results; an empty
  journal; ``last_council`` at council 0, tick -1, with the starting figures.

No I/O and no state other than the new entity.
"""

from typing import Final

from aimpire.sim.places import places_by_id
from aimpire.sim.rng import SITES, draw, stream_key, uniform_int
from aimpire.sim.state import Value, WorldState
from aimpire.sim.systems.survey import survey
from aimpire.sim.systems.tribe import CIV, FOOD
from aimpire.sim.world.m0_rules import M0Rules

_CAMP_STREAM, _CAMP_N = SITES["m0_camp"]
_WORLDGEN_TICK: Final = 0
FULL_RATION: Final = 1000


def camp_for(state: WorldState, seat: int) -> str:
    """The camp place id drawn for ``seat`` (0-based) from the run seed."""
    place_ids = sorted(places_by_id(state))
    if not place_ids:
        raise ValueError("the world has no places")
    key = stream_key(state.run_seed, _WORLDGEN_TICK, _CAMP_STREAM)
    return place_ids[uniform_int(draw(key, seat, _CAMP_N), len(place_ids))]


def place_tribe(state: WorldState, rules: M0Rules, *, civ_id: str = "C1", seat: int = 0) -> int:
    """Add the tribe for ``seat`` as civ ``civ_id``; return its entity id."""
    camp = camp_for(state, seat)
    stores: dict[str, Value] = {FOOD: rules.start_stores}
    policy: dict[str, Value] = {"allocations": [], "ration": FULL_RATION}
    last_council: dict[str, Value] = {
        "council": 0,
        "tick": -1,
        "population": rules.start_people,
        "stores": {FOOD: rules.start_stores},
    }
    fields: dict[str, Value] = {
        "civ_id": civ_id,
        "camp": camp,
        "population": rules.start_people,
        "stores": stores,
        "known": {},
        "names": {},
        "policy": policy,
        "tasks": [],
        "commitments": [],
        "last_results": [],
        "journal": "",
        "last_council": last_council,
        "carries": {},
        "task_times": {},
        "work": [],
    }
    eid = state.add_entity(CIV, fields)
    survey(state, state.entities[eid], camp, rules.scout_sight)
    return eid
