"""Property tests for M0a regrowth and value noise (Hypothesis)."""

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from aimpire.sim.fixed import PPM
from aimpire.sim.rng import Stream, stream_key
from aimpire.sim.systems.regrowth import regrowth_delta
from aimpire.sim.world.noise import value_noise

PERIODS = st.sampled_from([1, 30, 120])


@st.composite
def tiles(draw: st.DrawFn) -> tuple[int, int, int, int, int, int, int]:
    """(K, F, carry, r_ppm, r_per, s_ppm, s_per) with r + s <= 1 a tick, like the loader."""
    k = draw(st.integers(0, 200_000))
    f = draw(st.integers(0, k))
    r_per, s_per = draw(PERIODS), draw(PERIODS)
    r_ppm = draw(st.integers(0, PPM * r_per // 2))
    s_ppm = draw(st.integers(0, PPM * s_per // 2))
    period = np.lcm(r_per, s_per)
    carry = draw(st.integers(0, max(k * PPM * int(period) - 1, 0)))
    return k, f, carry, r_ppm, r_per, s_ppm, s_per


@given(tiles())
def test_one_step_is_exact_floor_and_bounded(tile: tuple[int, ...]) -> None:
    k, f, carry, r_ppm, r_per, s_ppm, s_per = tile
    delta, new_carry = regrowth_delta(
        np.array([[f]], dtype=np.int64),
        np.array([[k]], dtype=np.int64),
        np.array([[carry]], dtype=np.int64),
        (r_ppm, r_per),
        (s_ppm, s_per),
    )
    d, c = int(delta[0, 0]), int(new_carry[0, 0])
    assert 0 <= d <= k - f
    if k == 0:
        assert (d, c) == (0, 0)
        return
    period = r_per * s_per // int(np.gcd(r_per, s_per))
    num = (k - f) * (r_ppm * (period // r_per) * f + s_ppm * (period // s_per) * k) + carry
    assert (d, c) == divmod(num, k * PPM * period)


@settings(max_examples=30)
@given(
    k=st.integers(1, 50_000),
    f=st.integers(0, 50_000),
    ticks=st.integers(1, 200),
)
def test_food_rises_monotonically_and_stays_below_ceiling(k: int, f: int, ticks: int) -> None:
    food = np.array([[min(f, k)]], dtype=np.int64)
    ceiling = np.array([[k]], dtype=np.int64)
    carry = np.zeros_like(food)
    for _ in range(ticks):
        delta, carry = regrowth_delta(food, ceiling, carry, (2_400_000, 30), (30_000, 30))
        assert int(delta[0, 0]) >= 0
        food = food + delta
        assert int(food[0, 0]) <= k


@settings(max_examples=40)
@given(
    seed=st.integers(0, 2**64 - 1),
    rows=st.integers(1, 40),
    cols=st.integers(1, 40),
    cell=st.integers(1, 20),
    low=st.integers(0, PPM),
    span=st.integers(0, PPM),
)
def test_noise_stays_in_range_and_is_deterministic(
    *, seed: int, rows: int, cols: int, cell: int, low: int, span: int
) -> None:
    key = stream_key(seed, 0, Stream.WORLDGEN)
    grid = value_noise(key, 0, (rows, cols), cell, (low, low + span))
    assert grid.shape == (rows, cols)
    assert low <= int(grid.min()) <= int(grid.max()) <= low + span
    assert np.array_equal(grid, value_noise(key, 0, (rows, cols), cell, (low, low + span)))
