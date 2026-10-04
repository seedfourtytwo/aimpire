"""Integer quantiles and paired differences across seeds (LAB1 twin reports).

Why integers and nearest rank: the values are milli-units or counts, and a
report must be byte-identical for identical runs, so no float interpolation.

Quantile ``q`` (percent) of ``n`` sorted values is the nearest-rank value:
index ``ceil(q * n / 100) - 1``, clamped to ``0..n-1``. The median is the
lower median (index ``(n - 1) // 2``), as in the experiment reports. With few
seeds the 10-90 % band is simply the range: with 8 seeds the 10 % value is
the smallest and the 90 % value the largest.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

LOW_Q: Final = 10
HIGH_Q: Final = 90


def quantile(values: Sequence[int], q: int) -> int:
    """Nearest-rank ``q`` percent quantile of ``values`` (module docstring)."""
    if not values or not 0 <= q <= 100:
        raise ValueError("quantile needs values and 0 <= q <= 100")
    ordered = sorted(values)
    index = -(-q * len(ordered) // 100) - 1
    return ordered[min(max(index, 0), len(ordered) - 1)]


def lower_median(values: Sequence[int]) -> int:
    """The lower median: the middle value, or the lower of the two middle ones."""
    if not values:
        raise ValueError("lower_median needs values")
    ordered = sorted(values)
    return ordered[(len(ordered) - 1) // 2]


@dataclass(frozen=True, slots=True)
class Band:
    """Per-tick median and 10-90 % band of one series across seeds."""

    median: tuple[int, ...]
    low: tuple[int, ...]
    high: tuple[int, ...]


def band(series: Sequence[Sequence[int]]) -> Band:
    """The band of several equally long series (one per seed), tick by tick."""
    if not series or len({len(s) for s in series}) != 1:
        raise ValueError("a band needs one or more series of the same length")
    columns = list(zip(*series, strict=True))
    return Band(
        median=tuple(lower_median(c) for c in columns),
        low=tuple(quantile(c, LOW_Q) for c in columns),
        high=tuple(quantile(c, HIGH_Q) for c in columns),
    )


def paired_differences(
    baseline: Sequence[Sequence[int]], variant: Sequence[Sequence[int]]
) -> list[list[int]]:
    """Variant minus baseline, tick by tick, seed by seed (same seed order on both sides)."""
    if len(baseline) != len(variant):
        raise ValueError("paired differences need one baseline series per variant series")
    return [
        [v - b for b, v in zip(bs, vs, strict=True)]
        for bs, vs in zip(baseline, variant, strict=True)
    ]
