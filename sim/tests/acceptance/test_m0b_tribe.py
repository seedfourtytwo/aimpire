"""M0b acceptance: the tribe, work from the standing policy, and hunger (backlog M0b).

Written before the code, in the planning role (ADR-0016). Read-only for implementers.

What is tested is the physics the backlog states, through the public paths a
run uses: ``build_m0_run`` (rules from ``rules/v1``), decisions validated by
``validate_reply`` and committed by ``commit_decision`` (the council
barrier's path), and the ``m0`` preset in checked mode, which verifies every
system against the ledger as it runs (F3).
"""

import asyncio
import copy
import itertools
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import pytest

from aimpire.cognition.budget import BudgetGuard, Caps
from aimpire.cognition.council import Settled, decision_id_for
from aimpire.cognition.minds import build_provider, resolve_mind
from aimpire.cognition.observe import CouncilCall, build_observation
from aimpire.cognition.render import system_prompt
from aimpire.cognition.runner import run_with_councils
from aimpire.cognition.seats import Seat, seat_from_observation, seats_for
from aimpire.contracts.mind import Observation
from aimpire.experiments.m0_world import build_m0_run
from aimpire.experiments.worlds import World
from aimpire.lab.variant import resolve_variant
from aimpire.rules import load_calendar, load_m0_rules
from aimpire.sim.actions import DecisionLog, DecisionRecord, Reason, validate_reply
from aimpire.sim.actions.commit import commit_decision
from aimpire.sim.fixed import PPM
from aimpire.sim.hashing import state_hash
from aimpire.sim.places import places_by_id, travel_ticks
from aimpire.sim.state import Entity, Value, WorldState
from aimpire.sim.world.m0 import CEILING, FOOD

pytestmark = pytest.mark.acceptance

REPO = Path(__file__).resolve().parents[3]
RULES_V1 = REPO / "rules" / "v1"
CALENDAR = load_calendar(RULES_V1)
RULES = load_m0_rules(RULES_V1, CALENDAR)


def _run(seed: int = 1, settings: tuple[str, ...] = (), seats: int = 1) -> World:
    return build_m0_run(seed, RULES_V1, seats=seats, settings=settings, checked=True)


def _civ(world: World, seat: int = 0) -> dict[str, Any]:
    """The tribe's ``civ`` entity, loosely typed for reading nested fields in tests."""
    return cast(dict[str, Any], world.state.entities[world.civs[seat][1]])


def _observe(world: World, council: int, seat: int = 0) -> Observation:
    civ_id = world.civs[seat][0]
    call = CouncilCall(civ_id, council, decision_id_for(civ_id, council), world.state.tick + 10)
    return build_observation(world.state, call, world.calendar)


def _decide(
    world: World,
    council: int,
    *,
    allocations: Sequence[tuple[str, str, int]] = (),
    orders: Sequence[tuple[str, str, int]] = (),
    seat: int = 0,
) -> DecisionRecord:
    """Validate and commit one reply through the barrier's path."""
    obs = _observe(world, council, seat)
    reply: dict[str, Any] = {
        "decision_id": obs.decision_id,
        "policy": {
            "allocations": [{"activity": a, "place": p, "share": s} for a, p, s in allocations],
            "ration": 1000,
        },
        "orders": [
            {"kind": k, "place": p, "target": "", "qty": q, "text": ""} for k, p, q in orders
        ],
        "messages": [],
        "commitments": [],
        "beliefs": [],
        "names": [],
        "journal": "",
        "annal": "",
    }
    seat_view = seat_from_observation(obs)
    record = validate_reply(
        world.state, obs.civ_id, obs.version, reply, seat=seat_view, log=DecisionLog()
    )
    commit_decision(world.state, world.civs[seat][1], record)
    return record


def _place_food(state: WorldState, place: str) -> int:
    tiles = places_by_id(state)[place].tiles
    return sum(int(state.layers[FOOD][r, c]) for r, c in tiles)


def _neighbour(world: World) -> str:
    camp = str(_civ(world)["camp"])
    return places_by_id(world.state)[camp].neighbours[0]


def _ledger_sum(world: World, material: str, kind: str, since: int = 0) -> int:
    entries = world.scheduler.ledger.entries
    return sum(
        e.delta for e in entries if e.material == material and e.kind == kind and e.tick >= since
    )


# --- Conservation -----------------------------------------------------------


def test_foraging_conserves_food() -> None:
    """Every mu of food is accounted for: tiles + stores change only by REGROWTH, CONSUME, SPOIL.

    Checked mode already verifies each system against its ledger entries; on
    top of that the whole cycle balances, and HARVEST only moves food.
    """
    world = _run(3)
    camp = str(_civ(world)["camp"])
    _decide(world, 1, allocations=[("FORAGE", camp, 600), ("FORAGE", _neighbour(world), 400)])
    state = world.state
    start = int(state.layers[FOOD].sum()) + int(_civ(world)["stores"]["food"])
    world.scheduler.run(state, 90)
    end = int(state.layers[FOOD].sum()) + int(_civ(world)["stores"]["food"])

    harvested_tiles = _ledger_sum(world, "food", "HARVEST")
    harvested_stores = _ledger_sum(world, "stores", "HARVEST")
    assert harvested_stores > 0, "the foragers must bring food in"
    assert harvested_tiles == -harvested_stores, "HARVEST moves food, it never makes or loses any"
    regrowth = _ledger_sum(world, "food", "REGROWTH")
    eaten = _ledger_sum(world, "stores", "CONSUME")
    spoiled = _ledger_sum(world, "stores", "SPOIL")
    assert eaten < 0 and spoiled < 0
    assert end - start == regrowth + eaten + spoiled


def test_no_food_means_deaths_and_no_negative_stores() -> None:
    """With no wild food and empty stores, people die (LIFE draws) and stores stay at zero.

    The tribe dies out; an extinct tribe is left alone by every system.
    """
    world = _run(5)
    state = world.state
    state.layers[CEILING][...] = 0
    state.layers[FOOD][...] = 0
    civ = _civ(world)
    civ["stores"] = {"food": 0}
    _decide(world, 1, allocations=[("FORAGE", str(civ["camp"]), 1000)])
    people = [int(civ["population"])]
    for _ in range(400):
        world.scheduler.step(state)
        assert int(civ["stores"]["food"]) == 0
        people.append(int(civ["population"]))
    assert all(a >= b for a, b in itertools.pairwise(people)), "no births in M0"
    # 5 % a tick with nothing eaten: about 19 of 30 dead after 20 ticks.
    assert 8 <= people[0] - people[20] <= 28
    assert people[-1] == 0
    deaths_text = [e for e in state.entities.values() if e.get("kind") == "evidence"]
    assert any("hunger" in str(e["text"]) for e in deaths_text)

    frozen = copy.deepcopy(civ)
    world.scheduler.run(state, 30)
    assert civ == frozen, "an extinct tribe does nothing"


# --- Orders -----------------------------------------------------------------


def test_move_camp_takes_travel_time() -> None:
    """MOVE_CAMP takes the true travel ticks; nobody forages on the way; arrival is recorded."""
    world = _run(2)
    state = world.state
    civ = _civ(world)
    old = str(civ["camp"])
    dest = _neighbour(world)
    walk = travel_ticks(state, old, dest)  # Earth walking speed: tile steps = ticks
    assert walk > 0
    _decide(world, 1, allocations=[("FORAGE", old, 1000)], orders=[("MOVE_CAMP", dest, 0)])
    start = state.tick
    for _ in range(walk):
        world.scheduler.step(state)
        assert civ["camp"] == old
    assert _ledger_sum(world, "stores", "HARVEST") == 0, "nobody forages while the camp moves"
    world.scheduler.step(state)
    assert civ["camp"] == dest
    arrived = [
        e
        for e in state.entities.values()
        if e.get("kind") == "evidence" and e.get("place") == dest and e.get("tick") == start + walk
    ]
    assert len(arrived) == 1
    assert civ["known"][dest]["seen_tick"] == start + walk
    assert _ledger_sum(world, "stores", "HARVEST", since=start + walk) > 0, "work resumes"


def test_scout_reveals_snapshot_not_live_truth() -> None:
    """A scout's report is a dated snapshot; later changes to the place do not reach the tribe."""
    world = _run(4)
    state = world.state
    civ = _civ(world)
    target = _neighbour(world)
    before = set(civ["known"])
    walk = travel_ticks(state, str(civ["camp"]), target)
    _decide(world, 1, orders=[("SCOUT", target, 2)])
    start = state.tick
    world.scheduler.run(state, walk + 1)
    seen = civ["known"][target]
    assert seen["seen_tick"] == start + walk
    assert seen["seen"]["food"] == _place_food(state, target)
    assert set(civ["known"]) - before, "scouting discovers places next to the target"
    assert any(
        e.get("kind") == "evidence" and e.get("place") == target and e.get("tick") == start + walk
        for e in state.entities.values()
    )

    snapshot = copy.deepcopy(seen)
    for r, c in places_by_id(state)[target].tiles:
        state.layers[FOOD][r, c] = 0  # the truth changes after the scouts left
    world.scheduler.run(state, 5)
    assert civ["known"][target] == snapshot
    view = {p.place_id: p for p in _observe(world, 2).places}[target]
    assert view.last_seen_tick == start + walk
    assert view.seen == f"food {snapshot['seen']['food'] // 1000}"


def test_unknown_place_order_rejected_without_leak() -> None:
    """An order or allocation naming an unseen place is rejected exactly like a non-existent one."""
    worlds = [_run(6), _run(6)]
    civ = _civ(worlds[0])
    unseen = sorted(set(places_by_id(worlds[0].state)) - set(civ["known"]))[0]
    records = [
        _decide(w, 1, allocations=[("FORAGE", place, 500)], orders=[("SCOUT", place, 1)])
        for w, place in zip(worlds, (unseen, "PL99"), strict=True)
    ]
    for record in records:
        assert record.orders == ()
        assert {r.reason for r in record.rejections} == {Reason.UNKNOWN_ENTITY}
    assert records[0].rejections == records[1].rejections
    assert _civ(worlds[0])["last_results"] == [[0, "", "", "REJECTED", "UNKNOWN_ENTITY"]]
    for w in worlds:
        w.scheduler.run(w.state, 15)
    assert state_hash(worlds[0].state) == state_hash(worlds[1].state)
    assert _observe(worlds[0], 2) == _observe(worlds[1], 2)


# --- Order of processing ----------------------------------------------------


def _reordered(value: Value) -> Value:
    """The same value with every mapping's key order reversed."""
    if isinstance(value, dict):
        return {k: _reordered(value[k]) for k in reversed(list(value))}
    if isinstance(value, list):
        return [_reordered(v) for v in value]
    return value


def test_turn_order_independent() -> None:
    """Two tribes foraging one place: the outcome does not depend on dict or id order.

    Tribes compete through the per-tick shuffled turn order; reversing the
    insertion order of every entity and mapping changes nothing.
    """
    world = _run(8, seats=2)
    state = world.state
    shared = str(_civ(world, 0)["camp"])
    for seat in (0, 1):
        civ = _civ(world, seat)
        civ["camp"] = shared
        civ["policy"] = {"allocations": [["FORAGE", shared, 1000]], "ration": 1000}
    twin = _run(8, seats=2)
    twin.state.entities = {
        eid: cast(Entity, _reordered(e)) for eid, e in reversed(list(state.entities.items()))
    }
    assert state_hash(world.state) == state_hash(twin.state)
    assert list(twin.state.entities) != list(world.state.entities)
    for w in (world, twin):
        w.scheduler.run(w.state, 60)
    assert state_hash(world.state) == state_hash(twin.state)
    assert _ledger_sum(world, "stores", "HARVEST") > 0


# --- Physics from W0 --------------------------------------------------------


def test_lower_gravity_increases_carry_per_trip() -> None:
    """Carry load comes from W0 (∝ 1/g): lighter worlds bring more food home per trip."""
    harvests: list[int] = []
    for gravity in (500_000, 1_000_000, 1_500_000):
        settings = (f"world.gravity={gravity}",)
        world = _run(9, settings)
        civ = _civ(world)
        _decide(world, 1, allocations=[("FORAGE", str(civ["camp"]), 1000)])
        world.scheduler.step(world.state)
        took = _ledger_sum(world, "stores", "HARVEST")
        load = resolve_variant(RULES_V1, settings).derived.carry_load
        # Foraging the camp's own place: zero travel, one trip a tick, first tick no carry.
        assert took == RULES.start_people * RULES.carry_per_trip * load // PPM
        harvests.append(took)
    assert harvests[0] > harvests[1] > harvests[2]


# --- End to end -------------------------------------------------------------


class _Hashes:
    """A council sink that keeps checkpoint hashes and council outcomes."""

    def __init__(self) -> None:
        self.checkpoints: list[tuple[int, str, str]] = []
        self.outcomes: list[str] = []

    def record_council(self, tick: int, council: int, settled: Sequence[Settled]) -> None:
        self.outcomes.extend(s.record.outcome.value for s in settled)

    def checkpoint(self, state: WorldState, label: str) -> None:
        self.checkpoints.append((state.tick, label, state_hash(state)))


def _full_loop(seed: int) -> tuple[_Hashes, World]:
    world = build_m0_run(seed, RULES_V1)
    mind = resolve_mind("rule:forage_nearest", REPO)
    seats = [Seat(civ, eid, mind, build_provider(mind)) for civ, eid in world.civs]
    sink = _Hashes()
    build = seats_for(
        seats, calendar=world.calendar, every_ticks=10, renderer="places", system=system_prompt()
    )
    asyncio.run(
        run_with_councils(
            world.state,
            world.scheduler,
            ticks=2 * CALENDAR.ticks_per_year,
            every_ticks=10,
            checkpoint_every=30,
            seats_for=build,
            gate=BudgetGuard(Caps()),
            sink=sink,
        )
    )
    return sink, world


def test_full_loop_two_years_is_deterministic() -> None:
    """Runner + RuleProvider for two game years, twice: identical checkpoint hashes."""
    first, world = _full_loop(11)
    second, _ = _full_loop(11)
    assert first.checkpoints == second.checkpoints
    assert len(first.outcomes) == 2 * CALENDAR.ticks_per_year // 10
    assert set(first.outcomes) <= {"VALID", "PARTIAL"}
    assert len({h for *_, h in first.checkpoints}) > 10, "the world must change"
    civ = _civ(world)
    assert len(civ["known"]) > 3, "the scouts discovered places"
    assert _ledger_sum(world, "stores", "HARVEST") > 0
