"""Property: no change to another civilization or to world truth reaches an observation (F5c)."""

from typing import Any

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from aimpire.cognition.observe import CouncilCall, build_observation, observation_hash
from aimpire.sim.calendar import Calendar
from aimpire.sim.places import grid_blocks
from aimpire.sim.state import WorldState

CAL = Calendar(ticks_per_season=30, seasons_per_year=4)
CALL = CouncilCall(civ_id="C01", council=2, decision_id="D2", next_council_tick=20)
_PLACES = [f"PL0{i}" for i in range(1, 7)]


def _civ(civ_id: str, journal: str, food: int, known: list[str]) -> dict[str, Any]:
    return {
        "civ_id": civ_id,
        "camp": "PL01",
        "population": 5,
        "stores": {"food": food},
        "known": {pid: {"seen_tick": 1, "seen": {"food": food}} for pid in known},
        "names": {},
        "policy": {"allocations": [], "ration": 1000},
        "tasks": [],
        "commitments": [],
        "last_results": [],
        "journal": journal,
        "last_council": {"council": 1, "tick": 0, "population": 5, "stores": {}},
    }


def _world(
    other_journal: str, other_food: int, other_known: list[str], tile_food: int, cause: str
) -> WorldState:
    s = WorldState(run_seed=3, rules_version="v1", rules_hash="x")
    s.add_layer("food", np.full((6, 6), tile_food, dtype=np.int64))
    grid_blocks(s, 2, 3)
    s.add_entity("civ", _civ("C01", "ours", 4_000, ["PL01", "PL02"]))
    s.add_entity("civ", _civ("C02", other_journal, other_food, other_known))
    s.add_entity("evidence", {"civ": "C02", "tick": 3, "place": "PL05", "text": other_journal,
                              "witnesses": [9]})  # fmt: skip
    s.add_entity("event", {"tick": 3, "place": "PL02", "hidden_cause": cause})
    s.tick = 10
    return s


@settings(max_examples=60, deadline=None)
@given(
    journal=st.text(max_size=40),
    food=st.integers(min_value=0, max_value=10**9),
    known=st.lists(st.sampled_from(_PLACES), unique=True),
    tile=st.integers(min_value=0, max_value=10**9),
    cause=st.text(max_size=20),
)
def test_other_civ_and_truth_never_reach_the_observation(
    journal: str, food: int, known: list[str], tile: int, cause: str
) -> None:
    reference = observation_hash(build_observation(_world("", 0, [], 0, ""), CALL, CAL))
    varied = build_observation(_world(journal, food, known, tile, cause), CALL, CAL)
    assert observation_hash(varied) == reference
