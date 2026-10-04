"""Exact integer roots, rounded division and a sine table for the physics laws (ADR-0020).

Why integers even at load time: derived rates are hashed, and ``math.pow`` or
``math.sin`` may differ in the last bit across platforms and library builds,
which would split hashes (ADR-0007). Everything here is exact integer
arithmetic, so every platform derives the same bytes.

Rounding rule, used by every law: **round to nearest, ties upward**. It is
monotonic (a larger exact value never rounds to a smaller integer), so the
laws keep the direction physics gives them, and it is never more than half a
unit (half a ppm) from the exact value.
"""

from math import isqrt
from typing import Final

SINE_SCALE: Final = 1_000_000_000
"""``SINE_TABLE`` entries are sin(k degrees) times this, rounded to nearest."""

SINE_TABLE: Final = (
    0, 17_452_406, 34_899_497, 52_335_956, 69_756_474, 87_155_743,
    104_528_463, 121_869_343, 139_173_101, 156_434_465, 173_648_178, 190_808_995,
    207_911_691, 224_951_054, 241_921_896, 258_819_045, 275_637_356, 292_371_705,
    309_016_994, 325_568_154, 342_020_143, 358_367_950, 374_606_593, 390_731_128,
    406_736_643, 422_618_262, 438_371_147, 453_990_500, 469_471_563, 484_809_620,
    500_000_000, 515_038_075, 529_919_264, 544_639_035, 559_192_903, 573_576_436,
    587_785_252, 601_815_023, 615_661_475, 629_320_391, 642_787_610, 656_059_029,
    669_130_606, 681_998_360, 694_658_370, 707_106_781, 719_339_800, 731_353_702,
    743_144_825, 754_709_580, 766_044_443, 777_145_961, 788_010_754, 798_635_510,
    809_016_994, 819_152_044, 829_037_573, 838_670_568, 848_048_096, 857_167_301,
    866_025_404, 874_619_707, 882_947_593, 891_006_524, 898_794_046, 906_307_787,
    913_545_458, 920_504_853, 927_183_855, 933_580_426, 939_692_621, 945_518_576,
    951_056_516, 956_304_756, 961_261_696, 965_925_826, 970_295_726, 974_370_065,
    978_147_601, 981_627_183, 984_807_753, 987_688_341, 990_268_069, 992_546_152,
    994_521_895, 996_194_698, 997_564_050, 998_629_535, 999_390_827, 999_847_695,
    1_000_000_000,
)  # fmt: skip
"""sin(0..90 degrees), one entry per whole degree. Generated once, offline; never at load time."""

MILLI: Final = 1_000
"""Milli-degrees per degree."""


def div_nearest(numer: int, denom: int) -> int:
    """``numer / denom`` rounded to nearest, ties up. Both arguments non-negative, ``denom > 0``."""
    if numer < 0 or denom <= 0:
        raise ValueError(f"need numer >= 0 and denom > 0, got {numer}, {denom}")
    return (2 * numer + denom) // (2 * denom)


def sqrt_nearest(n: int) -> int:
    """The square root of ``n`` rounded to nearest.

    ``isqrt`` floors to ``r``. The exact root is at least ``r + 1/2`` exactly
    when ``n >= r*r + r + 1/4``, that is ``n - r*r > r`` for integers (no ties).
    """
    r = isqrt(n)
    return r + 1 if n - r * r > r else r


def icbrt(n: int) -> int:
    """The floor of the cube root of ``n >= 0``: the largest ``c`` with ``c**3 <= n``.

    Integer Newton iteration from a start at or above the root; each step
    stays at or above it and strictly decreases until it reaches the floor.
    """
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if n < 2:
        return n
    x = 1 << -(-n.bit_length() // 3)  # 2**ceil(bits/3) >= cube root of n
    while True:
        y = (2 * x + n // (x * x)) // 3
        if y >= x:
            return x
        x = y


def cbrt_ratio_nearest(numer: int, denom: int) -> int:
    """The cube root of ``numer / denom`` rounded to nearest, ties up.

    The floor of the cube root of a non-negative rational equals the floor of
    the cube root of its integer floor, because cubes of integers are integers.
    Then ``c + 1`` is nearer exactly when ``numer / denom >= (c + 1/2)**3``,
    compared exactly as ``8 * numer >= (2c + 1)**3 * denom``.
    """
    if numer < 0 or denom <= 0:
        raise ValueError(f"need numer >= 0 and denom > 0, got {numer}, {denom}")
    c = icbrt(numer // denom)
    return c + 1 if 8 * numer >= (2 * c + 1) ** 3 * denom else c


def sin_scaled(milli_degrees: int) -> int:
    """sin of an angle in 0..90 degrees, times ``SINE_SCALE * MILLI`` (exact integer).

    Linear interpolation between whole degrees of ``SINE_TABLE``. The result
    is never rounded, so it is exact for the table and monotonic in the angle.
    Accuracy: the chord of a 1-degree step is at most 3.9e-5 below the true
    sine (h**2/8 with h = 1 degree in radians), well under the validity of the
    season law itself.
    """
    if not 0 <= milli_degrees <= 90 * MILLI:
        raise ValueError(f"angle must be in 0..90_000 milli-degrees, got {milli_degrees}")
    degree, part = divmod(milli_degrees, MILLI)
    if part == 0:
        return SINE_TABLE[degree] * MILLI
    low, high = SINE_TABLE[degree], SINE_TABLE[degree + 1]
    return low * MILLI + (high - low) * part
