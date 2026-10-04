"""Properties of the exact integer helpers behind the W0 physics laws."""

from fractions import Fraction

from hypothesis import given
from hypothesis import strategies as st

from aimpire.rules.intmath import (
    SINE_SCALE,
    SINE_TABLE,
    cbrt_ratio_nearest,
    div_nearest,
    icbrt,
    sin_scaled,
    sqrt_nearest,
)

BIG = st.integers(min_value=0, max_value=10**30)
POSITIVE = st.integers(min_value=1, max_value=10**15)


@given(BIG)
def test_icbrt_is_the_floor_cube_root(n: int) -> None:
    c = icbrt(n)
    assert c**3 <= n < (c + 1) ** 3


@given(BIG)
def test_sqrt_nearest_is_nearest(n: int) -> None:
    r = sqrt_nearest(n)
    # |r - sqrt(n)| <= 1/2  <=>  (r - 1/2)^2 <= n <= (r + 1/2)^2, in exact quarters
    assert r == 0 or (2 * r - 1) ** 2 <= 4 * n
    assert 4 * n <= (2 * r + 1) ** 2


@given(BIG, POSITIVE)
def test_div_nearest_is_nearest_ties_up(numer: int, denom: int) -> None:
    q = div_nearest(numer, denom)
    assert Fraction(2 * q - 1, 2) <= Fraction(numer, denom) < Fraction(2 * q + 1, 2)


@given(BIG, POSITIVE)
def test_cbrt_ratio_nearest_is_nearest(numer: int, denom: int) -> None:
    c = cbrt_ratio_nearest(numer, denom)
    x = Fraction(numer, denom)
    assert c == 0 or Fraction(2 * c - 1, 2) ** 3 <= x
    assert x < Fraction(2 * c + 1, 2) ** 3


@given(st.integers(min_value=0, max_value=89_999))
def test_sine_is_monotonic_and_matches_the_table(milli_degrees: int) -> None:
    assert sin_scaled(milli_degrees) <= sin_scaled(milli_degrees + 1)
    if milli_degrees % 1_000 == 0:
        assert sin_scaled(milli_degrees) == SINE_TABLE[milli_degrees // 1_000] * 1_000


def test_sine_table_ends() -> None:
    assert SINE_TABLE[0] == 0
    assert SINE_TABLE[30] == SINE_SCALE // 2
    assert SINE_TABLE[90] == SINE_SCALE
    assert len(SINE_TABLE) == 91
