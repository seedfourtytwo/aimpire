"""PLUMBING world ``stub``: no physics. Real experiments use ``world: m0``.

Why it still exists: the F6 acceptance tests (``test_f6cd_qualify_batch``)
run their experiment files in ``world: stub``, and those tests are read-only
for implementers. M0c registered ``m0`` beside it; delete this module when the
creator moves those tests to ``m0``. It was built because ``aimpire batch``
needed a world before any world rules existed: the toy world of the F5e
acceptance tests, extended to the full m0 ``civ`` layout so the real
observation builder, renderers and validator run unchanged:

* an 8 by 8 map cut into four 4 by 4 places (``grid_blocks``);
* one ``drift`` system that adds a seeded amount (0 to 6 milli-units) to one
  tile each tick, so the state hash depends on the seed;
* one civilization per seat, ``C1``, ``C2``, ..., camped in turn at PL01 to
  PL04, each knowing every place from a snapshot taken at tick 0.

Nothing here is physics. Results from this world measure the plumbing
(replies, outcomes, rotation, reproducibility), never a civilization.
"""

from collections.abc import Mapping
from typing import Final

import numpy as np

from aimpire.experiments.worlds import World
from aimpire.sim.calendar import Calendar
from aimpire.sim.places import grid_blocks, places_by_id
from aimpire.sim.rng import Stream, draw, uniform_int
from aimpire.sim.scheduler import Preset, Scheduler, System, SystemSpec, TickContext
from aimpire.sim.state import Value, WorldState

STUB: Final = "stub"
RULES_VERSION: Final = "stub-0"
RULES_HASH: Final = "stub-world-placeholder"
CALENDAR: Final = Calendar(ticks_per_season=30, seasons_per_year=4)
MAP_TILES: Final = 8
BLOCK_TILES: Final = 4
PEOPLE: Final = 10
FOOD_MU: Final = 50_000  # milli-units: 50 person-days
DRIFT_MAX_MU: Final = 7  # exclusive bound of the per-tick drift draw


class _Drift:
    """Adds a seeded amount to tile (0, 0) each tick: a stand-in for real systems."""

    name = "drift"
    cadence = "tick"
    sequential = False

    def step(self, state: WorldState, ctx: TickContext) -> None:
        u = draw(ctx.key(Stream.GROWTH), 0, 0)
        state.layers["food"][0, 0] += uniform_int(u, DRIFT_MAX_MU)


def _drift(_params: Mapping[str, Value]) -> System:
    return _Drift()  # pyright: ignore[reportReturnType] (class attributes satisfy the protocol)


def _civ(civ_id: str, camp: str, place_ids: list[str]) -> dict[str, Value]:
    """A civilization in the m0 layout documented in ``cognition.civ_record``."""
    stores: dict[str, Value] = {"food": FOOD_MU}
    known: dict[str, Value] = {pid: {"seen_tick": 0, "seen": {}} for pid in place_ids}
    return {
        "civ_id": civ_id,
        "camp": camp,
        "population": PEOPLE,
        "stores": stores,
        "known": known,
        "names": {},
        "policy": {"allocations": [], "ration": 1000},
        "tasks": [],
        "commitments": [],
        "last_results": [],
        "journal": "",
        "last_council": {"council": 0, "tick": -1, "population": PEOPLE, "stores": dict(stores)},
    }


def build_stub_world(seed: int, seats: int) -> World:
    """A fresh stub world for ``seed`` with ``seats`` civilizations."""
    if seats < 1:
        raise ValueError(f"seats must be >= 1, got {seats}")
    state = WorldState(run_seed=seed, rules_version=RULES_VERSION, rules_hash=RULES_HASH)
    state.add_layer("food", np.zeros((MAP_TILES, MAP_TILES), dtype=np.int64))
    grid_blocks(state, BLOCK_TILES, BLOCK_TILES)
    place_ids = sorted(places_by_id(state))
    civs: list[tuple[str, int]] = []
    for i in range(seats):
        civ_id = f"C{i + 1}"
        camp = place_ids[i % len(place_ids)]
        civs.append((civ_id, state.add_entity("civ", _civ(civ_id, camp, place_ids))))
    scheduler = Scheduler(Preset(STUB, [SystemSpec("drift")]), {"drift": _drift}, CALENDAR)
    return World(state=state, scheduler=scheduler, calendar=CALENDAR, civs=tuple(civs))
