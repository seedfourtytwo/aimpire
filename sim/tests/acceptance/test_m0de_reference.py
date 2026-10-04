"""M0d acceptance: the reference ensemble of the four M0 baselines (backlog M0d, ADR-0014 s. 1).

Written in the planning role (ADR-0016) together with the reference runner.
Read-only for implementers.

``experiments/m0-reference.yaml`` runs ``rule:random``, ``rule:greedy``,
``rule:half_full`` and ``rule:msy`` on 200 world seeds for five game years and
reports bands (10th percentile, lower median, 90th percentile) of population,
deaths, stores and the wild food near the camp at every year boundary. The
full ensemble is run by hand and committed under ``docs/experiments/``:

    aimpire batch experiments/m0-reference.yaml --out docs/experiments --jobs 2

CI runs a subset: the file's first 10 seeds for one game year. It must give
the same data twice (every number and every final state hash) and match the
table below, recorded from the first run of the runner (2026-10-04) and
consistent with the M0c calibration (half full keeps all 30 people on seeds
1 to 10; greedy and random lose most of theirs within the first year).
"""

import json
from pathlib import Path
from typing import Any

import pytest

from aimpire.experiments.experiment import file_hash
from aimpire.experiments.reference import load_reference, reference_data, run_reference
from aimpire.rules import load_calendar, load_m0_rules

pytestmark = pytest.mark.acceptance

REPO = Path(__file__).resolve().parents[3]
REFERENCE = REPO / "experiments" / "m0-reference.yaml"
DOCS = REPO / "docs" / "experiments"
CALENDAR = load_calendar(REPO / "rules" / "v1")
START_PEOPLE = load_m0_rules(REPO / "rules" / "v1", CALENDAR).start_people
BASELINES = ("rule:random", "rule:greedy", "rule:half_full", "rule:msy")
SUBSET_SEEDS = 10
SUBSET_TICKS = CALENDAR.ticks_per_year  # one game year
MEASURES = ("population", "deaths", "stores_mu", "near_camp_mu")

# At the end of the subset (tick 120): (10th percentile, lower median, 90th percentile).
EXPECTED: dict[str, dict[str, tuple[int, int, int]]] = {
    "rule:random": {
        "population": (2, 19, 30),
        "deaths": (0, 0, 27),
        "stores_mu": (0, 0, 339_920),
        "near_camp_mu": (0, 983, 530_498),
    },
    "rule:greedy": {
        "population": (4, 17, 23),
        "deaths": (0, 13, 24),
        "stores_mu": (0, 0, 0),
        "near_camp_mu": (48_127, 148_917, 281_751),
    },
    "rule:half_full": {
        "population": (30, 30, 30),
        "deaths": (0, 0, 0),
        "stores_mu": (613_212, 1_468_996, 1_699_951),
        "near_camp_mu": (1_525_283, 2_309_535, 2_514_357),
    },
    "rule:msy": {
        "population": (30, 30, 30),
        "deaths": (0, 0, 0),
        "stores_mu": (820_763, 1_849_842, 2_167_110),
        "near_camp_mu": (1_083_883, 1_568_347, 1_779_593),
    },
}
# Each band is computed per measure, so a median of deaths need not equal 30 minus the
# median of people (random: 19 alive and 0 dead are both lower medians of 10 seeds).


@pytest.fixture(scope="module")
def twice() -> tuple[dict[str, Any], dict[str, Any]]:
    """The subset's data, computed twice from scratch."""
    spec = load_reference(REFERENCE)
    seeds = spec.seeds[:SUBSET_SEEDS]
    first = reference_data(spec, run_reference(spec, seeds=seeds, ticks=SUBSET_TICKS))
    second = reference_data(spec, run_reference(spec, seeds=seeds, ticks=SUBSET_TICKS))
    return first, second


def _end(data: dict[str, Any], mind: str, measure: str) -> tuple[int, int, int]:
    (entry,) = [m for m in data["minds"] if m["mind"] == mind]
    band = entry["bands"][measure]
    return band["q10"][-1], band["median"][-1], band["q90"][-1]


def test_reference_file_is_the_registered_design() -> None:
    """Four baselines, 200 distinct seeds, five years, a checkpoint at every year boundary."""
    spec = load_reference(REFERENCE)
    assert tuple(m.label for m in spec.minds) == BASELINES
    assert len(spec.seeds) == 200 and len(set(spec.seeds)) == 200
    assert spec.ticks == 5 * CALENDAR.ticks_per_year
    assert spec.checkpoint_every == CALENDAR.ticks_per_year
    assert spec.world == "m0"


def test_reference_bands_reproduce(twice: tuple[dict[str, Any], dict[str, Any]]) -> None:
    """A 10-seed subset gives identical numbers twice and matches the stored table."""
    first, second = twice
    assert first == second
    assert first["checkpoints"] == [0, SUBSET_TICKS]
    assert len(first["runs"]) == len(BASELINES) * SUBSET_SEEDS
    found = {mind: {m: _end(first, mind, m) for m in MEASURES} for mind in BASELINES}
    assert found == EXPECTED


def test_bands_are_ordered_and_physical(twice: tuple[dict[str, Any], dict[str, Any]]) -> None:
    """Bands are ordered; nobody is born in M0; half full keeps more people than the others."""
    data, _ = twice
    for entry in data["minds"]:
        for measure in MEASURES:
            band = entry["bands"][measure]
            for lo, mid, hi in zip(band["q10"], band["median"], band["q90"], strict=True):
                assert lo <= mid <= hi
    for run in data["runs"]:
        assert run["final"]["population"] + run["final"]["deaths"] == START_PEOPLE
    alive = {mind: _end(data, mind, "population")[1] for mind in BASELINES}
    assert alive["rule:half_full"] == START_PEOPLE
    assert alive["rule:half_full"] > alive["rule:greedy"]
    assert alive["rule:half_full"] > alive["rule:random"]


def test_committed_reference_matches_its_file() -> None:
    """The committed full ensemble was made from the current reference file and is complete."""
    data = json.loads((DOCS / "m0-reference.json").read_text(encoding="utf-8"))
    assert data["reference"]["file_hash"] == file_hash(REFERENCE)
    assert len(data["reference"]["seeds"]) == 200
    assert data["checkpoints"] == list(range(0, 5 * SUBSET_TICKS + 1, SUBSET_TICKS))
    assert [m["mind"] for m in data["minds"]] == list(BASELINES)
    assert len(data["runs"]) == 200 * len(BASELINES)
    page = (DOCS / "m0-reference.md").read_text(encoding="utf-8")
    for chart in data["charts"]:
        assert (DOCS / chart).is_file()
        assert f"]({chart})" in page
