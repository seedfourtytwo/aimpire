"""Property tests for aimpire.sim.fixed: exactness against rational arithmetic."""

import math
from fractions import Fraction

from hypothesis import given
from hypothesis import strategies as st

from aimpire.sim.fixed import PPM, apply_rate, stochastic_round

values = st.integers(min_value=0, max_value=10**12)
rates = st.integers(min_value=0, max_value=PPM)
periods = st.integers(min_value=1, max_value=480)


@given(values, rates, periods, st.integers(min_value=1, max_value=200))
def test_running_total_is_floor_of_exact(value: int, ppm: int, per: int, ticks: int) -> None:
    carry = total = 0
    for _ in range(ticks):
        delta, carry = apply_rate(value, ppm, per, carry)
        total += delta
    assert total == math.floor(Fraction(value * ppm * ticks, PPM * per))


@given(values, rates, periods)
def test_delta_never_exceeds_value_per_period(value: int, ppm: int, per: int) -> None:
    delta, carry = apply_rate(value, ppm, per, PPM * per - 1)
    assert 0 <= delta <= value
    assert 0 <= carry < PPM * per


@given(
    st.integers(min_value=0, max_value=10**15),
    st.integers(min_value=1, max_value=10**9),
    st.integers(min_value=0, max_value=2**64 - 1),
)
def test_stochastic_round_is_floor_or_ceil(numer: int, denom: int, u: int) -> None:
    out = stochastic_round(numer, denom, u)
    assert out in {numer // denom, -(-numer // denom)}
