"""Unit tests for M0a worldgen, regrowth, presets and the per-tile fraction helper."""

import time
from pathlib import Path

import numpy as np
import pytest

from aimpire.lab.variant import resolve_variant
from aimpire.rules import load_calendar, load_m0_rules
from aimpire.sim.derived import DerivedWorld
from aimpire.sim.fixed import PPM, apply_fraction_array
from aimpire.sim.presets import EARTH_RATES, PRESETS, m0_quantities, system_registry
from aimpire.sim.rng import Stream, stream_key
from aimpire.sim.scheduler import PresetError, Scheduler
from aimpire.sim.systems.regrowth import regrowth_delta
from aimpire.sim.world.m0 import CEILING, FERTILITY, FOOD, build_m0_world, tile_ceiling
from aimpire.sim.world.noise import value_noise

RULES_V1 = Path(__file__).resolve().parents[3] / "rules" / "v1"
CALENDAR = load_calendar(RULES_V1)
RULES = load_m0_rules(RULES_V1, CALENDAR)
KEY = stream_key(9, 0, Stream.WORLDGEN)
R_SEASON = (2_400_000, 30)
S_SEASON = (30_000, 30)


def _grid(*values: int) -> np.ndarray:
    return np.array([list(values)], dtype=np.int64)


def test_earth_rates_match_the_derived_earth_world() -> None:
    assert resolve_variant(RULES_V1, []).derived == EARTH_RATES


def test_noise_with_cell_one_is_the_lattice_itself() -> None:
    grid = value_noise(KEY, 0, (5, 7), 1, (100, 200))
    assert grid.shape == (5, 7)
    assert grid.dtype == np.int64
    assert 100 <= int(grid.min()) <= int(grid.max()) <= 200
    assert len(np.unique(grid)) > 10


def test_noise_is_smooth_inside_a_cell() -> None:
    """Neighbouring tiles differ by at most one lattice step's share: span / cell, plus rounding."""
    low, high, cell = 300_000, 1_000_000, 16
    grid = value_noise(KEY, 0, (64, 64), cell, (low, high))
    step = (high - low) // cell + 1
    assert int(np.abs(np.diff(grid, axis=0)).max()) <= step
    assert int(np.abs(np.diff(grid, axis=1)).max()) <= step


def test_noise_lattice_corners_are_draws_and_n_separates_sites() -> None:
    a = value_noise(KEY, 0, (33, 33), 16, (0, PPM))
    b = value_noise(KEY, 1, (33, 33), 16, (0, PPM))
    assert not np.array_equal(a, b)
    assert np.array_equal(a, value_noise(KEY, 0, (33, 33), 16, (0, PPM)))


def test_noise_refuses_bad_arguments() -> None:
    with pytest.raises(ValueError, match="shape"):
        value_noise(KEY, 0, (0, 4), 1, (0, 1))
    with pytest.raises(ValueError, match="cell"):
        value_noise(KEY, 0, (4, 4), 0, (0, 1))
    with pytest.raises(ValueError, match="low"):
        value_noise(KEY, 0, (4, 4), 1, (5, 1))
    with pytest.raises(OverflowError):
        value_noise(KEY, 0, (4, 4), 2**31, (0, PPM))


def test_flat_fertility_gives_the_base_ceiling() -> None:
    fert = np.full((2, 2), PPM, dtype=np.int64)
    assert np.all(tile_ceiling(RULES, EARTH_RATES, fert) == RULES.food_ceiling)
    half = np.full((2, 2), PPM // 2, dtype=np.int64)
    assert np.all(tile_ceiling(RULES, EARTH_RATES, half) == RULES.food_ceiling // 2)


def test_ceiling_overflow_is_refused() -> None:
    huge = DerivedWorld(*([PPM] * 8), plant_ceiling=2**62)
    with pytest.raises(OverflowError):
        tile_ceiling(RULES, huge, np.full((1, 1), PPM, dtype=np.int64))


def test_world_layers_and_places() -> None:
    state = build_m0_world(1, RULES, EARTH_RATES, rules_version="v1", rules_hash="h")
    assert set(state.layers) == {FERTILITY, CEILING, FOOD}
    assert int(state.layers[CEILING].min()) >= RULES.food_ceiling * RULES.fertility_min // PPM
    state.validate()


def test_regrowth_never_passes_ceiling_and_restarts_from_zero() -> None:
    food, ceiling = _grid(0, 5_000, 9_999, 10_000, 0), _grid(10_000, 10_000, 10_000, 10_000, 0)
    delta, carry = regrowth_delta(food, ceiling, np.zeros_like(food), R_SEASON, S_SEASON)
    assert np.all(delta <= ceiling - food)
    assert delta[0, 3] == 0 and delta[0, 4] == 0 and carry[0, 4] == 0
    # From zero only the seed term acts: 0.1 % of K a tick = 10 mu.
    assert delta[0, 0] == 10
    # Half full: r K / 4 + s K / 2 = 200 + 5 mu.
    assert delta[0, 1] == 205


def test_regrowth_carry_keeps_tiny_growth() -> None:
    """A tiny ceiling still regrows: 1 mu of K grows by s K = 0.001 mu a tick, every 1000 ticks."""
    food, ceiling = _grid(0), _grid(1)
    carry = np.zeros_like(food)
    total = 0
    for _ in range(1_000):
        delta, carry = regrowth_delta(food, ceiling, carry, R_SEASON, S_SEASON)
        total += int(delta.sum())
    assert total == 1


def test_regrowth_mixed_periods_use_the_common_period() -> None:
    food, ceiling = _grid(5_000), _grid(10_000)
    zero = np.zeros_like(food)
    same, _ = regrowth_delta(food, ceiling, zero, R_SEASON, S_SEASON)
    per_tick_seed, _ = regrowth_delta(food, ceiling, zero, R_SEASON, (1_000, 1))
    assert int(same[0, 0]) == int(per_tick_seed[0, 0])


def test_regrowth_overflow_is_refused() -> None:
    food, ceiling = _grid(0), _grid(2**40)
    with pytest.raises(OverflowError):
        regrowth_delta(food, ceiling, np.zeros_like(food), R_SEASON, S_SEASON)


def test_fraction_helper_checks_inputs() -> None:
    one = _grid(1)
    with pytest.raises(TypeError):
        apply_fraction_array(one.astype(np.int32), one, one)  # pyright: ignore[reportArgumentType]
    with pytest.raises(ValueError, match="one shape"):
        apply_fraction_array(_grid(1, 2), one, one)
    with pytest.raises(ValueError, match="denominators"):
        apply_fraction_array(one, _grid(0), _grid(0))
    with pytest.raises(ValueError, match="below its denominator"):
        apply_fraction_array(one, _grid(2), _grid(2))
    with pytest.raises(ValueError, match=">= 0"):
        apply_fraction_array(_grid(-1), _grid(2), _grid(0))
    with pytest.raises(OverflowError):
        apply_fraction_array(_grid(2**62), _grid(2**62), _grid(0))
    q, c = apply_fraction_array(_grid(7), _grid(3), _grid(2))
    assert (int(q[0, 0]), int(c[0, 0])) == (3, 0)


def test_preset_systems_refuse_parameters() -> None:
    registry = system_registry(RULES)
    with pytest.raises(PresetError, match="no preset parameters"):
        registry["regrowth"]({"rate": 1})


def test_m0_runs_1200_ticks_quickly() -> None:
    """64 x 64 for ten game years in checked mode: well under a few seconds (about 0.1 s)."""
    state = build_m0_world(2, RULES, EARTH_RATES, rules_version="v1", rules_hash="h")
    state.layers[FOOD][...] = state.layers[CEILING] // 10
    scheduler = Scheduler(PRESETS["m0"], system_registry(RULES), CALENDAR, m0_quantities())
    start = time.perf_counter()
    scheduler.run(state, 1_200)
    assert time.perf_counter() - start < 3.0
    assert np.array_equal(state.layers[FOOD], state.layers[CEILING])
