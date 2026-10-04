"""Unit tests for the observation builder and renderers (F5c).

The acceptance tests fix the leak, hash and determinism guarantees; these
cover the arithmetic, windows, caps and error paths.
"""

import re
from typing import Any

import numpy as np
import pytest

from aimpire.cognition.observe import CouncilCall, build_observation, grid_layout
from aimpire.cognition.render import GridLayout, render_grid, render_places, system_prompt
from aimpire.contracts.vocabulary import MAX_EVENTS
from aimpire.sim.calendar import Calendar
from aimpire.sim.hashing import state_hash
from aimpire.sim.places import grid_blocks, travel_ticks_within
from aimpire.sim.state import WorldState

CAL = Calendar(ticks_per_season=30, seasons_per_year=4)


def _civ(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "civ_id": "C01",
        "camp": "PL01",
        "population": 10,
        "stores": {"food": 9_999, "wood": 500},
        "known": {"PL01": {"seen_tick": 0, "seen": {}}},
        "names": {},
        "policy": {"allocations": [], "ration": 1000},
        "tasks": [],
        "commitments": [],
        "last_results": [],
        "journal": "",
        "last_council": {"council": 0, "tick": -1, "population": 12, "stores": {"food": 12_000}},
    }
    base.update(over)
    return base


def _state(tick: int = 5, **civ: Any) -> WorldState:
    s = WorldState(run_seed=1, rules_version="v1", rules_hash="x")
    s.add_layer("food", np.zeros((6, 6), dtype=np.int64))
    grid_blocks(s, 2, 3)  # 3 rows by 2 columns of places
    s.add_entity("civ", _civ(**civ))
    s.tick = tick
    return s


def _call(next_tick: int = 10) -> CouncilCall:
    return CouncilCall(civ_id="C01", council=1, decision_id="D1", next_council_tick=next_tick)


def test_status_rounds_down_and_reports_changes() -> None:
    obs = build_observation(_state(), _call(), CAL)
    assert obs.status.food_days == 9 and obs.status.food_days_change == 9 - 12
    assert obs.status.population_change == -2
    [wood] = obs.status.stores
    assert (wood.material, wood.qty, wood.change) == ("wood", 0, 0)


def test_calendar_is_one_based_and_next_council_not_negative() -> None:
    obs = build_observation(_state(tick=125), _call(next_tick=100), CAL)
    assert obs.calendar.year == 2 and obs.calendar.season == "1 of 4"
    assert obs.calendar.ticks_to_next_council == 0


def test_events_are_windowed_and_capped_newest_kept() -> None:
    s = _state(tick=100, last_council={"council": 1, "tick": 10, "population": 10, "stores": {}})
    for tick in (5, 10, *range(11, 11 + MAX_EVENTS + 5), 101):
        s.add_entity(
            "evidence",
            {"civ": "C01", "tick": tick, "place": "PL01", "text": "", "witnesses": [3, 1]},
        )
    obs = build_observation(s, _call(), CAL)
    ticks = [e.tick for e in obs.events]
    assert len(ticks) == MAX_EVENTS and ticks == sorted(ticks)
    assert ticks[0] == 16 and ticks[-1] == 10 + MAX_EVENTS + 5  # 5, 10 and 101 are outside
    assert obs.events[0].witnesses == ["P0001", "P0003"]


def test_places_sorted_with_own_names_and_travel() -> None:
    known = {pid: {"seen_tick": 3, "seen": {"food": 2_500}} for pid in ("PL06", "PL02", "PL01")}
    obs = build_observation(_state(known=known, names={"PL02": "Ash"}), _call(), CAL)
    assert [p.place_id for p in obs.places] == ["PL01", "PL02", "PL06"]
    assert [p.name for p in obs.places] == ["", "Ash", ""]
    assert obs.places[0].travel_ticks == 0 and obs.places[0].seen == "food 2"
    assert obs.places[2].travel_ticks > obs.places[1].travel_ticks


def test_travel_falls_back_to_lower_bound_when_known_places_do_not_connect() -> None:
    # 3 rows by 2 columns; PL06 is known but PL03 to PL05 are not, so no known route.
    known = {pid: {"seen_tick": 0, "seen": {}} for pid in ("PL01", "PL06")}
    state = _state(known=known)
    assert travel_ticks_within(state, "PL01", "PL06", {"PL01", "PL06"}) is None
    obs = build_observation(state, _call(), CAL)
    # Centroids (0, 1) and (4, 4): Manhattan distance 7.
    assert {p.place_id: p.travel_ticks for p in obs.places} == {"PL01": 0, "PL06": 7}


def test_camp_counts_as_known_for_routes() -> None:
    # The camp PL01 is not in "known", but routes may start there.
    known = {"PL02": {"seen_tick": 0, "seen": {}}}
    obs = build_observation(_state(known=known), _call(), CAL)
    assert obs.places[0].travel_ticks == 3


def test_empty_snapshot_reads_nothing() -> None:
    obs = build_observation(_state(), _call(), CAL)
    assert obs.places[0].seen == "nothing"


def test_unknown_place_or_civ_is_an_error() -> None:
    with pytest.raises(KeyError):
        build_observation(_state(known={"PL99": {"seen_tick": 0, "seen": {}}}), _call(), CAL)
    with pytest.raises(KeyError):
        build_observation(_state(civ_id="C09"), _call(), CAL)


def test_malformed_civ_field_is_rejected() -> None:
    with pytest.raises(TypeError):
        build_observation(_state(population="ten"), _call(), CAL)
    with pytest.raises(ValueError):
        build_observation(_state(commitments=[["BE_AT", "PL01", 0, 3, "SOON"]]), _call(), CAL)


def test_two_civ_entities_with_one_id_is_an_error() -> None:
    s = _state()
    s.add_entity("civ", _civ())
    with pytest.raises(ValueError):
        build_observation(s, _call(), CAL)


def test_building_does_not_change_the_state() -> None:
    s = _state()
    before = state_hash(s)
    build_observation(s, _call(), CAL)
    assert state_hash(s) == before


def test_grid_layout_ranks_blocks() -> None:
    layout = grid_layout(_state())
    assert (layout.rows, layout.cols) == (3, 2)
    assert layout.cells[0] == ("PL01", 1, 1) and layout.cells[-1] == ("PL06", 3, 2)


def test_grid_renderer_needs_a_cell_for_every_known_place() -> None:
    obs = build_observation(_state(), _call(), CAL)
    with pytest.raises(ValueError):
        render_grid(obs, GridLayout(rows=1, cols=1, cells=(("PL02", 1, 1),)))


def test_empty_sections_say_none() -> None:
    text = render_places(build_observation(_state(), _call(), CAL))
    for name in ("events", "messages", "last_results", "knowledge", "journal"):
        body = text.split(f"## {name}\n", 1)[1].split("\n", 1)[0]
        assert body == "none"


# ADR-0019 section 4: the prompt names no institution, belief or role. A first
# version of the lexicon check; the versioned list belongs to a later item.
_BANNED = frozenset(
    {
        "king", "chief", "priest", "tax", "law", "religion", "god", "democracy", "market",
        "tribe", "leader", "ruler", "worship", "temple", "prophet", "scripture", "trade",
        "money", "state", "government",
    }
)  # fmt: skip


def test_system_prompt_is_neutral() -> None:
    words = set(re.findall(r"[a-z]+", system_prompt().lower()))
    assert not words & _BANNED
