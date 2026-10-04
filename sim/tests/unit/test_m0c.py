"""Unit tests for M0c: map scale, the baseline kit and policies, and ``aimpire run`` plumbing."""

from fractions import Fraction
from pathlib import Path

import pytest

from aimpire.cli.main import main
from aimpire.cognition.baseline_kit import (
    fit,
    read_ceilings,
    seen_food_mu,
    shares_for,
    workers_for,
    write_ceilings,
)
from aimpire.cognition.baselines import RULE_NAMES, rule_provider
from aimpire.cognition.council import decision_id_for
from aimpire.cognition.disclosed import default_disclosed
from aimpire.cognition.m0_baselines import greedy, half_full, msy, random_shares
from aimpire.cognition.observe import CouncilCall, build_observation
from aimpire.contracts.mind import Observation
from aimpire.experiments.m0_world import build_m0_run
from aimpire.experiments.play import reproduce_command
from aimpire.experiments.worlds import world_names
from aimpire.rules import DEFAULT_RULES_DIR, RulesError, load_map_scale
from aimpire.sim.fixed import PPM
from aimpire.sim.places import places_by_id, travel_tiles
from aimpire.sim.scale import TILE_PER_TICK, MapScale, map_scale
from aimpire.sim.systems.survey import walk_ticks
from aimpire.sim.systems.work import apportion

SCALE = load_map_scale(DEFAULT_RULES_DIR)


def _observation(seed: int = 1) -> Observation:
    world = build_m0_run(seed, DEFAULT_RULES_DIR)
    call = CouncilCall("C1", 1, decision_id_for("C1", 1), 10)
    return build_observation(world.state, call, world.calendar)


# --- map scale ---------------------------------------------------------------------------


def test_map_scale_rounds_up_and_scales_with_walking_speed() -> None:
    scale = MapScale(tile=1_000, walk_per_tick=20_000)
    assert [scale.ticks(n) for n in (0, 1, 16, 20, 21, 32, 96)] == [0, 1, 1, 1, 2, 2, 5]
    assert scale.ticks(16, PPM // 2) == 2  # half the speed, twice the time
    assert scale.ticks(32, 2 * PPM) == 1
    assert TILE_PER_TICK.ticks(16) == 16
    with pytest.raises(ValueError):
        MapScale(tile=0, walk_per_tick=1)
    with pytest.raises(ValueError):
        MapScale.from_mapping({"tile": 1})
    with pytest.raises(ValueError):
        MapScale.from_mapping({"tile": 1.5, "walk_per_tick": 2})


def test_load_map_scale_refuses_bad_files(tmp_path: Path) -> None:
    (tmp_path / "scale.yaml").write_text("tile: 1000\nwalk_per_tick: 20000\nextra: 1\n")
    with pytest.raises(RulesError):
        load_map_scale(tmp_path)


def test_m0_world_stores_the_scale_and_neighbours_are_one_tick_away() -> None:
    world = build_m0_run(2, DEFAULT_RULES_DIR)
    assert map_scale(world.state) == SCALE
    places = places_by_id(world.state)
    for pid, place in places.items():
        for other in place.neighbours:
            assert travel_tiles(world.state, pid, other) == 16
            assert walk_ticks(world.state, pid, other, PPM) == 1
    assert walk_ticks(world.state, "PL01", "PL16", PPM) == 5  # far corner, 96 km


# --- the baseline kit -------------------------------------------------------------------


def test_seen_food_and_ceilings_round_trip_through_the_journal() -> None:
    obs = _observation()
    for place in obs.places:
        assert seen_food_mu(place) == int(place.seen.split()[1]) * 1000
    ceilings = read_ceilings(obs)
    journal = write_ceilings(ceilings)
    later = obs.model_copy(update={"journal": journal, "places": []})
    assert read_ceilings(later) == ceilings


def test_workers_and_shares_give_each_line_its_people() -> None:
    assert workers_for(Fraction(0), 1, 10_000) == 0
    assert workers_for(Fraction(10_000), 0, 10_000) == 1
    assert workers_for(Fraction(10_001), 1, 10_000) == 4  # 3 ticks a trip, rounded up
    assert fit([("FORAGE", "PL01", 20), ("FORAGE", "PL02", 20)], 30) == [
        ("FORAGE", "PL01", 15),
        ("FORAGE", "PL02", 15),
    ]
    lines = [("FORAGE", "PL01", 4), ("FORAGE", "PL02", 13), ("SCOUT", "PL01", 1)]
    shares = shares_for(lines, 30)
    assert sum(s for *_, s in shares) <= 1000
    got = {(a, p): n for a, p, n in apportion(30, shares)}
    for activity, place, people in lines:
        assert got[(activity, place)] >= people


# --- the policies -----------------------------------------------------------------------


def test_policies_reply_validly_and_scout_the_camp() -> None:
    obs = _observation(5)
    camp = next(p.place_id for p in obs.places if p.travel_ticks == 0)
    for reply in (greedy(obs), half_full(obs, default_disclosed()), msy(obs, default_disclosed())):
        lines = {(a.activity, a.place) for a in reply.policy.allocations}
        assert ("SCOUT", camp) in lines
        assert sum(a.share for a in reply.policy.allocations) <= 1000
    shares = random_shares(obs).policy.allocations
    assert sum(a.share for a in shares) == 1000
    assert {a.activity for a in shares} == {"FORAGE"}
    assert random_shares(obs) == random_shares(obs), "seeded by the observation"
    assert random_shares(obs, seed=1) != random_shares(obs, seed=2)


def test_half_full_leaves_places_at_or_below_half() -> None:
    obs = _observation(6)
    ceilings = read_ceilings(obs)
    halved = [
        p.model_copy(update={"seen": f"food {ceilings[p.place_id] // 2000}"}) for p in obs.places
    ]
    start = obs.model_copy(update={"journal": write_ceilings(ceilings), "places": halved})
    reply = half_full(start, default_disclosed())
    assert {a.activity for a in reply.policy.allocations} == {"SCOUT"}
    assert msy(start, default_disclosed()).policy.allocations != reply.policy.allocations


def test_msy_target_is_the_disclosed_optimum() -> None:
    d = default_disclosed()
    assert d.msy_stock() == (1 - d.regrowth_s / d.regrowth_r) / 2
    assert d.msy_yield(1_000_000) == 1_000_000 * (d.regrowth_r + d.regrowth_s) ** 2 / (
        4 * d.regrowth_r
    )


def test_registry_knows_every_baseline_and_m0_is_a_world() -> None:
    assert {"random", "greedy", "half_full", "msy", "hold", "forage_nearest"} <= RULE_NAMES
    assert rule_provider("msy").describe().model == "msy"
    with pytest.raises(KeyError):
        rule_provider("nope")
    assert "m0" in world_names()


# --- aimpire run plumbing ---------------------------------------------------------------


def test_reproduce_command_drops_the_out_folder() -> None:
    argv = ["run", "m0", "--seed", "2", "--out", "/tmp/x", "--set", "world.gravity=950000"]
    assert reproduce_command(argv) == "aimpire run m0 --seed 2 --set world.gravity=950000"
    assert reproduce_command(["run", "m0", "--out=/tmp/y"]) == "aimpire run m0"


def test_run_refuses_bad_input(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = str(tmp_path / "runs")
    assert main(["run", "m0", "--mind", "rule:nope", "--ticks", "5", "--out", out]) == 2
    assert main(["run", "m0", "--set", "world.gravity=0", "--ticks", "5", "--out", out]) == 2
    assert main(["run", "m0", "--ticks", "0", "--out", out]) == 2
    assert main(["run", "m0", "--mind", "mock", "--ticks", "5", "--out", out]) == 0
    assert main(["run", "m0", "--mind", "mock", "--ticks", "5", "--out", out]) == 2, "exists"
    assert "already exists" in capsys.readouterr().out
