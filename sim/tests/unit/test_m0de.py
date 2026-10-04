"""Unit tests for M0d and M0e: exact statistics, bands, measures, reference files, E0 options."""

from fractions import Fraction
from math import comb
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from aimpire.cognition.disclosed import _decimal  # pyright: ignore[reportPrivateUsage]
from aimpire.experiments.experiment import ExperimentError, load_experiment
from aimpire.experiments.measures import world_metrics
from aimpire.experiments.reference import is_reference, load_reference
from aimpire.experiments.stats import (
    describe,
    median_interval,
    paired,
    quantile,
    sign_p_ppm,
)
from aimpire.report.band_panels import Panel, band_panels_svg

# --- stats ---------------------------------------------------------------------------


def test_quantile_is_nearest_rank() -> None:
    values = [5, 1, 4, 2, 3]
    assert quantile(values, 0) == 1
    assert quantile(values, 500) == 3
    assert quantile([1, 2, 3, 4], 500) == 2  # the lower median
    assert quantile(values, 900) == 5
    assert quantile(list(range(1, 11)), 100) == 1
    assert quantile(list(range(1, 11)), 900) == 9
    with pytest.raises(ValueError):
        quantile([], 500)
    with pytest.raises(ValueError):
        quantile([1], 1001)


def test_median_interval_needs_six_values() -> None:
    assert median_interval([1, 2, 3, 4, 5]) is None
    assert median_interval([6, 1, 5, 2, 4, 3]) == (1, 6)  # coverage 1 - 2/64 = 96.9 %


@given(st.integers(min_value=6, max_value=300))
def test_median_interval_is_the_tightest_with_95_percent_coverage(n: int) -> None:
    low, high = median_interval(list(range(n)))  # type: ignore[misc]
    j = low + 1  # the interval is [x(j), x(n+1-j)]
    assert high == n - j
    tail = sum(comb(n, i) for i in range(j))  # P(B < j) * 2^n
    assert 2 * tail * 20 <= 2**n  # coverage at least 95 %
    tighter = tail + comb(n, j)
    assert j > (n + 1) // 2 - 1 or 2 * tighter * 20 > 2**n  # j + 1 would not be


def test_sign_test_p_values() -> None:
    assert sign_p_ppm(9, 1) == -(-11 * 1_000_000 // 1024)  # (C(10,9) + C(10,10)) / 2^10
    assert sign_p_ppm(0, 0) == 1_000_000
    assert sign_p_ppm(5, 0) == 31_250


def test_paired_counts_and_superiority() -> None:
    a = {1: 30, 2: 30, 3: 20, 4: 10}
    b = {1: 10, 2: 30, 3: 25, 4: 5, 9: 1}
    result = paired(a, b)
    assert (result["seeds"], result["wins"], result["ties"], result["losses"]) == (4, 2, 1, 1)
    assert result["superiority_ppm"] == (2 * 2 + 1) * 1_000_000 // 8
    assert result["median_diff"] == 0  # diffs 20, 0, -5, 5 -> lower median 0
    assert result["ci95_low"] is None  # 4 seeds cannot bound a median at 95 %
    with pytest.raises(ValueError):
        paired({1: 1}, {2: 1})


def test_describe_orders_its_numbers() -> None:
    d = describe(list(range(100)))
    assert d["min"] <= d["q10"] <= d["ci95_low"] <= d["median"]  # type: ignore[operator]
    assert d["median"] <= d["ci95_high"] <= d["q90"] <= d["max"]  # type: ignore[operator]


# --- measures --------------------------------------------------------------------------


def test_world_metrics_sum_the_seats_of_one_mind() -> None:
    data = {
        "checkpoints": [0, 10],
        "civs": {
            "C1": {"population": [30, 15], "deaths": [0, 15], "stores_mu": [9, 4],
                   "near_camp_mu": [7, 3]},
            "C2": {"population": [30, 30], "deaths": [0, 0], "stores_mu": [9, 8],
                   "near_camp_mu": [7, 6]},
        },
    }  # fmt: skip
    assert world_metrics(data, ["C1"])["survival_ppm"] == 500_000
    both = world_metrics(data, ["C1", "C2"])
    assert both == {
        "survival_ppm": 750_000,
        "final_population": 45,
        "deaths": 15,
        "final_stores_mu": 12,
        "final_near_camp_mu": 9,
    }


# --- disclosure ------------------------------------------------------------------------


def test_decimal_is_exact() -> None:
    assert _decimal(Fraction(2, 25)) == "0.08"
    assert _decimal(Fraction(1, 1000)) == "0.001"
    assert _decimal(Fraction(10)) == "10"
    assert _decimal(Fraction(-1, 4)) == "-0.25"
    assert _decimal(Fraction(1, 3)) == "1/3"


# --- bands chart -----------------------------------------------------------------------


def test_band_panels_wrap_and_share_scales() -> None:
    panels = [Panel(f"g{i}", [0, 1], [1, 2], [2, 3 + i]) for i in range(5)]
    svg = band_panels_svg([0, 10], panels, panel_width=100, panel_height=60, columns=4)
    assert 'width="442" height="134"' in svg  # 4 across, 2 rows, 14 px gaps
    assert svg.count("<polygon") == 5
    assert svg.count(">7</text>") == 2  # the shared top value, on each row's first panel
    with pytest.raises(ValueError):
        band_panels_svg([0, 10], [Panel("bad", [0], [1, 2], [2, 3])])


# --- reference and experiment files --------------------------------------------------------

REFERENCE = """\
kind: reference
id: ref-test
purpose: "test"
world: m0
ticks: 20
council_every: 10
checkpoint_every: 10
seeds: {first: 5, count: 3}
minds: [rule:greedy]
"""


def _write(tmp_path: Path, text: str, name: str = "file.yaml") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_reference_file_loads_and_refuses_bad_designs(tmp_path: Path) -> None:
    path = _write(tmp_path, REFERENCE)
    assert is_reference(path)
    spec = load_reference(path)
    assert spec.seeds == (5, 6, 7)
    assert [m.label for m in spec.minds] == ["rule:greedy"]
    for bad in (
        REFERENCE.replace("[rule:greedy]", "[mock]"),  # rule minds only
        REFERENCE.replace("world: m0", "world: stub"),  # no measures there
        REFERENCE.replace("kind: reference", "kind: other"),
        REFERENCE + "extra: 1\n",
        REFERENCE.replace("{first: 5, count: 3}", "[1, 1]"),
    ):
        with pytest.raises(ExperimentError):
            load_reference(_write(tmp_path, bad))
    assert not is_reference(_write(tmp_path, "id: x\n", "plain.yaml"))


EXPERIMENT = """\
id: e-test
hypothesis: "test"
metrics: {primary: survival_ppm}
world: m0
ticks: 10
council_every: 10
checkpoint_every: 10
seats: 1
seeds: [1]
replicates: 3
arms:
  - {id: a, knowledge_arm: A0, renderer: places, prompt: base, models: [mock], rules: disclosed}
"""


def test_experiment_options_are_checked(tmp_path: Path) -> None:
    exp = load_experiment(_write(tmp_path, EXPERIMENT))
    assert exp.arms[0].rules == "disclosed"
    assert exp.preregistration == ""
    for bad in (
        EXPERIMENT.replace("rules: disclosed", "rules: sometimes"),
        EXPERIMENT.replace("world: m0", "world: stub"),  # survival_ppm needs measures
        EXPERIMENT + "preregistration: missing.md\n",
    ):
        with pytest.raises(ExperimentError):
            load_experiment(_write(tmp_path, bad))
    _write(tmp_path, "the plan\n", "prereg.md")
    exp = load_experiment(_write(tmp_path, EXPERIMENT + "preregistration: prereg.md\n"))
    assert exp.preregistration == "prereg.md"
    assert len(exp.preregistration_hash) == 64
