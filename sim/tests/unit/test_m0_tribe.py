"""Unit tests for the M0b tribe: setup, work split, trips, moves, bookkeeping and hunger."""

from pathlib import Path
from typing import Any, cast

import pytest

from aimpire.cognition.civ_record import read_civ
from aimpire.cognition.observe import CouncilCall, build_observation
from aimpire.experiments.m0_world import build_m0_run
from aimpire.experiments.worlds import World
from aimpire.sim.actions import (
    AcceptedCommitment,
    AcceptedName,
    AcceptedOrder,
    DecisionRecord,
    Outcome,
    Reason,
    Rejection,
    StandingPolicy,
)
from aimpire.sim.actions.commit import commit_decision
from aimpire.sim.fixed import PPM, ceil_div, chance_fraction
from aimpire.sim.places import places_by_id, travel_ticks
from aimpire.sim.systems.forage import take_food
from aimpire.sim.systems.survey import in_sight, walk_ticks
from aimpire.sim.systems.work import apportion, trip_times
from aimpire.sim.world.m0 import FOOD
from aimpire.sim.world.tribe import camp_for

RULES_V1 = Path(__file__).resolve().parents[3] / "rules" / "v1"


def _world(seed: int = 1) -> World:
    return build_m0_run(seed, RULES_V1, checked=True)


def _civ(world: World) -> dict[str, Any]:
    return cast(dict[str, Any], world.state.entities[world.civs[0][1]])


def _record(
    world: World,
    council: int,
    *,
    orders: tuple[AcceptedOrder, ...] = (),
    commitments: tuple[AcceptedCommitment, ...] = (),
    rejections: tuple[Rejection, ...] = (),
    names: tuple[AcceptedName, ...] = (),
    policy: StandingPolicy | None = None,
) -> DecisionRecord:
    return DecisionRecord(
        decision_id=f"C1-K{council:04d}",
        civ_id="C1",
        council=council,
        tick=world.state.tick,
        contract="m0",
        observation_version="v",
        outcome=Outcome.VALID,
        policy=policy or StandingPolicy((), 1000),
        orders=orders,
        messages=(),
        commitments=commitments,
        beliefs=(),
        names=names,
        journal="",
        annal="",
        rejections=rejections,
        flags=(),
    )


def _commit(world: World, record: DecisionRecord) -> None:
    commit_decision(world.state, world.civs[0][1], record)


# --- Setup -------------------------------------------------------------------


def test_tribe_setup_layout_and_knowledge() -> None:
    world = _world(1)
    civ = read_civ(world.state, "C1")
    assert civ.camp == camp_for(world.state, 0)
    assert civ.population == 30 and dict(civ.stores) == {"food": 900_000}
    places = places_by_id(world.state)
    expected = {civ.camp, *places[civ.camp].neighbours}
    assert {pid for pid, _, _ in civ.known} == expected
    assert all(tick == 0 for _, tick, _ in civ.known)
    assert civ.allocations == () and civ.ration == 1000
    assert civ.last_council.tick == -1


def test_camp_is_drawn_from_the_seed() -> None:
    camps = {camp_for(_world(seed).state, 0) for seed in range(12)}
    assert len(camps) > 3
    assert camp_for(_world(4).state, 0) == camp_for(_world(4).state, 0)


def test_observation_builds_on_an_m0_world() -> None:
    world = _world(2)
    obs = build_observation(world.state, CouncilCall("C1", 1, "C1-K0001", 10), world.calendar)
    assert obs.status.population == 30 and obs.status.food_days == 900
    assert len(obs.places) == len(_civ(world)["known"])


# --- Helpers -----------------------------------------------------------------


def test_apportion_largest_remainder_and_ties() -> None:
    lines = [("FORAGE", "PL02", 500), ("FORAGE", "PL01", 500)]
    assert apportion(3, lines) == [("FORAGE", "PL01", 2), ("FORAGE", "PL02", 1)]
    assert apportion(10, [("FORAGE", "PL01", 333)]) == [("FORAGE", "PL01", 3)]
    split = apportion(7, [("FORAGE", "PL01", 600), ("SCOUT", "PL03", 400)])
    assert sum(n for *_, n in split) == 7
    with pytest.raises(ValueError):
        apportion(5, [("FORAGE", "PL01", 700), ("SCOUT", "PL01", 400)])


def test_take_food_sorted_order_and_cap() -> None:
    world = _world(3)
    place = places_by_id(world.state)["PL01"]
    layer = world.state.layers[FOOD]
    first, second = sorted(place.tiles)[:2]
    layer[first] = 5
    layer[second] = 7
    others = sum(int(layer[t]) for t in place.tiles) - 12
    assert take_food(world.state, place, 6) == 6
    assert int(layer[first]) == 0 and int(layer[second]) == 6
    assert take_food(world.state, place, 10**12) == 6 + others
    assert sum(int(layer[t]) for t in place.tiles) == 0


def test_walk_ticks_scales_with_walking_speed() -> None:
    world = _world(3)
    true = travel_ticks(world.state, "PL01", "PL02")
    assert walk_ticks(world.state, "PL01", "PL02", PPM) == true
    assert walk_ticks(world.state, "PL01", "PL02", PPM // 2) == 2 * true
    assert walk_ticks(world.state, "PL01", "PL02", 3 * PPM) == ceil_div(true, 3)
    assert walk_ticks(world.state, "PL01", "PL01", 1) == 0


def test_in_sight_is_the_place_and_its_edge_neighbours() -> None:
    places = places_by_id(_world(1).state)
    assert in_sight(places, "PL06", 16) == ["PL02", "PL05", "PL06", "PL07", "PL10"]


def test_trip_times_and_exact_helpers() -> None:
    times = trip_times(10, 4)
    assert (times.start, times.arrive, times.done) == (10, 14, 18)
    assert trip_times(10, 0).done == 11
    assert ceil_div(0, 3) == 0 and ceil_div(7, 7) == 1 and ceil_div(8, 7) == 2
    assert chance_fraction(0, 1, 10) and not chance_fraction(9, 1, 10)
    assert not chance_fraction(5, 0, 10) and chance_fraction(5, 11, 10)
    with pytest.raises(ValueError):
        chance_fraction(5, 1, 0)


# --- Work, trips and moves ---------------------------------------------------


def test_standing_scouts_report_and_discover() -> None:
    world = _world(5)
    civ = _civ(world)
    target = places_by_id(world.state)[civ["camp"]].neighbours[0]
    civ["policy"] = {"allocations": [["SCOUT", target, 1000]], "ration": 1000}
    before = set(civ["known"])
    world.scheduler.run(world.state, 2)
    assert set(civ["known"]) > before
    assert civ["known"][target]["seen_tick"] == 1


def test_forage_order_brings_one_load_each() -> None:
    world = _world(6)
    civ = _civ(world)
    place = places_by_id(world.state)[civ["camp"]].neighbours[0]
    walk = travel_ticks(world.state, civ["camp"], place)
    _commit(world, _record(world, 1, orders=(AcceptedOrder(0, "FORAGE", place, "", 3, ""),)))
    world.scheduler.run(world.state, walk + 1)
    harvest = [e for e in world.scheduler.ledger.entries if e.kind == "HARVEST"]
    assert sum(e.delta for e in harvest if e.material == "stores") == 3 * 10_000
    world.scheduler.run(world.state, walk)
    assert civ["tasks"][0][4] == "DONE"


def test_trip_fails_when_nobody_is_free_and_move_waits_for_trips() -> None:
    world = _world(7)
    civ = _civ(world)
    near = places_by_id(world.state)[civ["camp"]].neighbours[0]
    civ["population"] = 2
    orders = (
        AcceptedOrder(0, "SCOUT", near, "", 2, ""),
        AcceptedOrder(1, "SCOUT", near, "", 1, ""),
        AcceptedOrder(2, "MOVE_CAMP", near, "", 0, ""),
    )
    _commit(world, _record(world, 1, orders=orders))
    world.scheduler.step(world.state)
    statuses = [row[4] for row in civ["tasks"]]
    assert statuses == ["EN_ROUTE", "FAILED", "ORDERED"]
    assert civ["tasks"][2][3] == 2, "a move takes everyone"
    walk = travel_ticks(world.state, civ["camp"], near)
    world.scheduler.run(world.state, 2 * walk)
    assert [row[4] for row in civ["tasks"]] == ["DONE", "FAILED", "ORDERED"]
    world.scheduler.step(world.state)
    assert civ["tasks"][2][4] == "EN_ROUTE", "the move starts once the scouts are back"


# --- Bookkeeping -------------------------------------------------------------


def test_bookkeeping_results_commitments_names_snapshot() -> None:
    world = _world(8)
    civ = _civ(world)
    camp = civ["camp"]
    record = _record(
        world,
        1,
        orders=(AcceptedOrder(1, "SCOUT", camp, "", 1, ""),),
        rejections=(
            Rejection("orders[0]", Reason.UNKNOWN_ENTITY),
            Rejection("orders[1].text", Reason.CAP_EXCEEDED),
            Rejection("policy.allocations[0]", Reason.UNKNOWN_ENTITY),
        ),
        commitments=(
            AcceptedCommitment(0, "STOCK_AT_LEAST", "", 800, 2),
            AcceptedCommitment(1, "BE_AT", camp, 0, 3),
            AcceptedCommitment(2, "STOCK_AT_LEAST", camp, 10**9, 2),
        ),
        names=(AcceptedName(0, camp, "Home"),),
    )
    _commit(world, record)
    assert civ["last_results"] == [
        [0, "", "", "REJECTED", "UNKNOWN_ENTITY"],
        [1, "SCOUT", camp, "ACCEPTED", ""],
    ]
    assert civ["tasks"] == [["C1-K0001-O1", "SCOUT", camp, 1, "ORDERED"]]
    assert civ["names"] == {camp: "Home"}
    assert civ["last_council"] == {
        "council": 1,
        "tick": 0,
        "population": 30,
        "stores": {"food": 900_000},
    }
    assert [row[4] for row in civ["commitments"]] == ["PENDING"] * 3

    _commit(world, _record(world, 2))
    states = [row[4] for row in civ["commitments"]]
    assert states == ["MET", "PENDING", "MISSED"]
    _commit(world, _record(world, 3))
    assert civ["commitments"] == [["BE_AT", camp, 0, 3, "MET"]]
    _commit(world, _record(world, 4))
    assert civ["commitments"] == []


def test_finished_tasks_are_pruned_at_the_next_commit() -> None:
    world = _world(9)
    civ = _civ(world)
    _commit(world, _record(world, 1, orders=(AcceptedOrder(0, "SCOUT", civ["camp"], "", 1, ""),)))
    world.scheduler.run(world.state, 2)
    assert civ["tasks"][0][4] == "DONE"
    _commit(world, _record(world, 2))
    assert civ["tasks"] == [] and civ["task_times"] == {}


# --- Hunger ------------------------------------------------------------------


def test_ration_scales_the_food_eaten_and_spoilage_is_recorded() -> None:
    world = _world(10)
    civ = _civ(world)
    civ["policy"] = {"allocations": [], "ration": 500}
    world.scheduler.step(world.state)
    entries = world.scheduler.ledger.entries
    eaten = -sum(e.delta for e in entries if e.kind == "CONSUME")
    spoiled = -sum(e.delta for e in entries if e.kind == "SPOIL")
    assert eaten == 30 * 1000 // 2
    assert spoiled == (900_000 - eaten) * 600_000 // (PPM * 30)
    assert civ["population"] == 30, "a chosen half ration is not a shortfall"
