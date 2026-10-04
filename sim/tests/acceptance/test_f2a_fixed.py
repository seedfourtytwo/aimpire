"""F2a acceptance: integer fixed-point helpers (ADR-0012 section A).

Written by the planning model before implementation (ADR-0016). Read-only.
"""

import hashlib
import math
from fractions import Fraction

import numpy as np
import pytest

from aimpire.sim.fixed import PPM, apply_rate, apply_rate_array, chance_ppm, stochastic_round

pytestmark = pytest.mark.acceptance

N_DRAWS = 100_000


def _uniform_u64(i: int) -> int:
    """Independent test-side 64-bit draws (not the engine's rng, which is F2b)."""
    return int.from_bytes(
        hashlib.blake2b(i.to_bytes(8, "little"), digest_size=8).digest(), "little"
    )


def _within_binomial(hits: int, n: int, p: Fraction, z: float = 5.0) -> bool:
    mean = float(p) * n
    sd = math.sqrt(n * float(p) * (1 - float(p)))
    return abs(hits - mean) <= z * sd + 1


def test_ppm_is_one_million() -> None:
    assert PPM == 1_000_000


def test_apply_rate_matches_exact_fraction() -> None:
    """Summed deltas equal the floor of the exact rational total, every tick."""
    value, ppm, per_ticks = 777, 333, 7
    carry, total = 0, 0
    for tick in range(1, 10_001):
        delta, carry = apply_rate(value, ppm, per_ticks, carry)
        total += delta
        assert total == math.floor(Fraction(value * ppm * tick, PPM * per_ticks))
        assert 0 <= carry < PPM * per_ticks


def test_apply_rate_never_stalls() -> None:
    """A 1,000 ppm per-tick decay from 5,000 reaches zero (floor division alone sticks at 999)."""
    value, carry = 5_000, 0
    for _ in range(100_000):
        if value == 0:
            break
        delta, carry = apply_rate(value, 1_000, 1, carry)
        value -= delta
    assert value == 0


def test_slow_rate_accumulates() -> None:
    """10,000 ppm per year (1%) on a value held at 1,000 yields exactly 10 over a 120-tick year."""
    carry, total = 0, 0
    for _ in range(120):
        delta, carry = apply_rate(1_000, 10_000, 120, carry)
        total += delta
    assert total == 10
    assert carry == 0


def test_stochastic_round_is_unbiased() -> None:
    """E[stochastic_round(n, d, u)] == n / d, within binomial bounds."""
    numer, denom = 7, 3  # 2.333...
    results = [stochastic_round(numer, denom, _uniform_u64(i)) for i in range(N_DRAWS)]
    assert set(results) == {2, 3}
    ups = results.count(3)
    assert _within_binomial(ups, N_DRAWS, Fraction(1, 3))
    assert stochastic_round(9, 3, 12345) == 3  # exact division never rounds up


def test_chance_ppm_frequency() -> None:
    for ppm in (0, 1_000, 250_000, 999_999, PPM):
        hits = sum(chance_ppm(_uniform_u64(i), ppm) for i in range(N_DRAWS))
        assert _within_binomial(hits, N_DRAWS, Fraction(ppm, PPM))
    assert not any(chance_ppm(_uniform_u64(i), 0) for i in range(1_000))
    assert all(chance_ppm(_uniform_u64(i), PPM) for i in range(1_000))


@pytest.mark.parametrize(
    "args",
    [(-1, 10, 1, 0), (1, -10, 1, 0), (1, 10, 0, 0), (1, 10, 1, -1), (1, 10, 1, PPM)],
)
def test_negative_input_rejected(args: tuple[int, int, int, int]) -> None:
    """Negative values or rates, a non-positive period, or a carry outside [0, PPM*per_ticks)."""
    with pytest.raises(ValueError):
        apply_rate(*args)


def test_stochastic_round_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        stochastic_round(-1, 3, 0)
    with pytest.raises(ValueError):
        stochastic_round(1, 0, 0)


def test_array_matches_scalar() -> None:
    values = np.array([0, 1, 999, 5_000, 123_456_789], dtype=np.int64)
    carries = np.array([0, 5, 999_999, 17, 0], dtype=np.int64)
    deltas, new_carries = apply_rate_array(values, 1_000, 1, carries)
    assert deltas.dtype == np.int64 and new_carries.dtype == np.int64
    for i in range(len(values)):
        assert (int(deltas[i]), int(new_carries[i])) == apply_rate(
            int(values[i]), 1_000, 1, int(carries[i])
        )


def test_array_overflow_raises() -> None:
    values = np.array([0, 10**13], dtype=np.int64)
    with pytest.raises(OverflowError):
        apply_rate_array(values, PPM, 1, np.zeros(2, dtype=np.int64))


def test_array_rejects_negative_and_wrong_dtype() -> None:
    with pytest.raises(ValueError):
        apply_rate_array(np.array([-1], dtype=np.int64), 10, 1, np.zeros(1, dtype=np.int64))
    with pytest.raises(TypeError):
        apply_rate_array(np.array([1.0]), 10, 1, np.zeros(1, dtype=np.int64))
