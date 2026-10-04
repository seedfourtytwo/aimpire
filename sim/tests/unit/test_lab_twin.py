"""Unit tests for the LAB1 twin: divergence, bands, seeds, physics rows, harvest rate, charts."""

from pathlib import Path
from typing import Any, cast

import pytest

from aimpire.cli.lab_command import parse_seeds
from aimpire.cli.main import main
from aimpire.experiments.m0_world import build_m0_run
from aimpire.lab.divergence import first_divergence, world_parts_differing
from aimpire.lab.physics_view import change_text, physics_rows, times_earth
from aimpire.lab.twin import seeds_label
from aimpire.lab.variant import resolve_variant
from aimpire.report.bands import band, lower_median, paired_differences, quantile
from aimpire.report.harvest_rate import HarvestRate
from aimpire.report.twin import display
from aimpire.report.twin_charts import paired_difference_svg, small_multiples_svg
from aimpire.sim.fixed import PPM
from aimpire.sim.ledger import Ledger
from aimpire.sim.places import lower_bound_ticks, places_by_id, travel_ticks_within
from aimpire.sim.systems.survey import walk_ticks

REPO = Path(__file__).resolve().parents[3]
RULES_V1 = REPO / "rules" / "v1"


# --- Divergence --------------------------------------------------------------


def test_meta_is_never_a_divergence() -> None:
    a = {"meta": "1", "layer:food": "x", "entities:civ": "c"}
    b = {"meta": "2", "layer:food": "x", "entities:civ": "c"}
    assert world_parts_differing(a, b) == []
    b["entities:evidence"] = "e"
    assert world_parts_differing(a, b) == ["entities:evidence"], "a part on one side only differs"


def test_first_divergence_finds_tick_parts_and_end() -> None:
    same = {"meta": "m", "layer:food": "f", "entities:civ": "c"}
    later = {"meta": "m", "layer:food": "F", "entities:civ": "C"}
    healed = {"meta": "m", "layer:food": "f", "entities:civ": "C"}
    d = first_divergence(4, [0, 1, 2, 3], [same] * 4, [same, later, later, healed])
    assert (d.first_tick, d.first_parts, d.final_parts) == (
        1,
        ("entities:civ", "layer:food"),
        ("entities:civ",),
    )
    assert d.part_first_ticks == (("entities:civ", 1), ("layer:food", 1))
    assert d.to_json()["first_tick"] == 1


def test_first_divergence_never() -> None:
    same = {"meta": "m", "layer:food": "f"}
    d = first_divergence(1, [0, 1], [same, same], [same, same])
    assert (d.first_tick, d.first_parts, d.final_parts) == (None, (), ())
    with pytest.raises(ValueError, match="same"):
        first_divergence(1, [0, 1], [same], [same, same])


# --- Bands -------------------------------------------------------------------


def test_quantiles_are_nearest_rank() -> None:
    values = [5, 1, 4, 2, 3, 8, 7, 6]
    assert (quantile(values, 10), quantile(values, 90)) == (1, 8), "with 8 seeds: the range"
    assert lower_median(values) == 4
    assert quantile(list(range(1, 21)), 10) == 2
    with pytest.raises(ValueError):
        quantile([], 50)


def test_band_and_paired_differences() -> None:
    diffs = paired_differences([[1, 2], [3, 3]], [[2, 2], [1, 5]])
    assert diffs == [[1, 0], [-2, 2]]
    b = band(diffs)
    assert (b.median, b.low, b.high) == ((-2, 0), (-2, 0), (1, 2))


# --- Seeds, ids, physics rows, display ----------------------------------------


def test_parse_seeds() -> None:
    assert parse_seeds("1-8") == tuple(range(1, 9))
    assert parse_seeds("3") == (3,)
    assert parse_seeds("9, 1,4-5,4") == (1, 4, 5, 9)
    for bad in ("", "a", "5-2", "-1", "1-"):
        with pytest.raises(ValueError):
            parse_seeds(bad)


def test_seeds_label() -> None:
    assert seeds_label((1, 2, 3)) == "s1-3"
    assert seeds_label((1, 3)).startswith("s") and seeds_label((1, 3)) != seeds_label((1, 4))


def test_physics_rows_text() -> None:
    assert times_earth(974_679) == "0.975"
    assert change_text(974_679) == "-2.5 %"
    assert change_text(1_052_632) == "+5.3 %"
    assert change_text(PPM) == "0.0 %"
    rows = physics_rows(resolve_variant(RULES_V1, ["world.gravity=300000"]).derived)
    flagged = {r["law"] for r in rows if r["beyond_model"]}
    assert "walk_speed" in flagged and "plant_ceiling" not in flagged


def test_display_rounds_half_away_from_zero() -> None:
    assert [display(v, 1000) for v in (1499, 1500, -1500, -1499, 0)] == [1, 2, -2, -1, 0]


# --- Harvest per forager-tick ---------------------------------------------------


def test_harvest_rate_windows_ledger_and_foragers() -> None:
    world = build_m0_run(1, RULES_V1)
    eid = world.civs[0][1]
    civ = cast(dict[str, Any], world.state.entities[eid])
    ledger = Ledger()
    rate = HarvestRate(ledger, eid, window=2)
    civ["work"] = [["FORAGE", "PL01", 4], ["SCOUT", "PL02", 9]]
    ledger.record("stores", 8000, "HARVEST", "C1:PL01")
    ledger.record("stores", 5000, "HARVEST", "C2:PL01")  # another tribe
    ledger.record("stores", -3000, "CONSUME", "C1:walk")
    assert rate(world.state) == 2000
    civ["work"] = []
    assert rate(world.state) == 2000, "an idle day adds no forager-ticks"
    civ["work"] = [["FORAGE", "PL01", 4]]
    ledger.record("stores", 4000, "HARVEST", "C1:PL01")
    assert rate(world.state) == 1000, "the first day left the window"
    civ["work"] = []
    assert rate(world.state) == 1000
    assert rate(world.state) == 0, "nobody foraged in the window"


# --- Travel at a walking speed -------------------------------------------------


def test_known_travel_scales_with_walk_speed() -> None:
    world = build_m0_run(2, RULES_V1, settings=("world.gravity=600000",))
    state, slow = world.state, world.walk_speed
    places = places_by_id(state)
    camp = str(state.entities[world.civs[0][1]]["camp"])
    for pid in sorted(places):
        allowed = frozenset(places)
        known = travel_ticks_within(state, camp, pid, allowed, slow)
        assert known is not None
        assert known == walk_ticks(state, camp, pid, slow), "all places known: the true walk"
        assert lower_bound_ticks(state, camp, pid, slow) <= known
        assert lower_bound_ticks(state, camp, pid) <= lower_bound_ticks(state, camp, pid, slow)


# --- Charts --------------------------------------------------------------------


def test_small_multiples_and_difference_charts() -> None:
    ticks = list(range(5))
    panels = [(1, [1, 2, 3, 4, 5], [1, 2, 3, 4, 6]), (2, [5, 4, 3, 2, 1], [5, 4, 3, 2, 2])]
    svg = small_multiples_svg(ticks, panels, "people (count)", "variant")
    assert svg.count("<polyline") == 4
    assert svg.count("variant 6") == 1 and svg.count("baseline 5") == 1, "names on panel 1 only"
    assert "every panel 1 to 6" in svg
    diff = paired_difference_svg(ticks, band([[0, 0, 0, 0, 1], [0, 0, 0, 0, 1]]), "people")
    assert "<polygon" in diff and "median +1" in diff


# --- CLI -----------------------------------------------------------------------


def test_lab_twin_cli_refusals(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    base = ["lab", "twin", "m0", "--out", str(tmp_path), "--ticks", "10"]
    assert main([*base, "--seeds", "x"]) == 2
    assert main([*base, "--seeds", "1", "--set", "world.gravity=0"]) == 2
    assert main([*base, "--seeds", "1"]) == 0
    assert main([*base, "--seeds", "1"]) == 2, "a twin is never overwritten"
    assert "already exists" in capsys.readouterr().out
