"""Exact, integer statistics for experiment and reference reports (ADR-0014 section 5).

ADR-0014 asks for distributions, medians and intervals from bootstrap or
exact methods, never normal approximations on small samples. Everything here
is exact, distribution-free and integer, so a report is byte-stable and needs
no random draws:

* ``quantile``: the nearest-rank quantile at ``p`` permille, a value that
  occurred. At 500 it is the lower median used across the reports.
* ``median_interval``: a confidence interval for the median from order
  statistics. For ``n`` sorted values, ``[x(j), x(n+1-j)]`` covers the true
  median with probability ``1 - 2 P(B < j)``, ``B ~ Binomial(n, 1/2)``. We
  take the largest ``j`` whose coverage is at least 95 %, with whole-number
  arithmetic (``math.comb``). Below 6 values no such ``j`` exists and the
  interval is ``None``: too few runs to bound the median at 95 %.
* ``paired``: seed-by-seed differences between two minds on the same worlds
  (ADR-0014: the seed is the unit of analysis). It gives wins, ties and
  losses, the median difference with its exact interval, the probability
  of superiority ``P(A > B) + P(A = B) / 2`` in ppm (an effect size that
  needs no assumption about the shape of the distribution), and the exact
  one-sided sign-test p-values in each direction (``sign_p_ppm``).
"""

from collections.abc import Mapping, Sequence
from math import comb
from typing import Final

PPM: Final = 1_000_000
PERMILLE: Final = 1000
LOW_PERMILLE: Final = 100  # the 10th percentile of a band
HIGH_PERMILLE: Final = 900  # the 90th percentile of a band
CONFIDENCE_MISS: Final = (1, 20)  # 1 - 95 %: at most 1 in 20 outside, as a fraction


def quantile(values: Sequence[int], p_permille: int) -> int:
    """The nearest-rank quantile at ``p_permille`` (0 to 1000) of ``values``."""
    if not values:
        raise ValueError("no values")
    if not 0 <= p_permille <= PERMILLE:
        raise ValueError(f"p must be 0 to {PERMILLE} permille, got {p_permille}")
    ordered = sorted(values)
    rank = max(1, -(-p_permille * len(ordered) // PERMILLE))  # ceil(p n), at least 1
    return ordered[rank - 1]


def median_interval(values: Sequence[int]) -> tuple[int, int] | None:
    """The exact order-statistic 95 % interval of the median, or ``None`` below 6 values."""
    n = len(values)
    miss_num, miss_den = CONFIDENCE_MISS
    best = 0
    tail = 0  # sum of C(n, i) for i < j
    for j in range(1, (n + 1) // 2 + 1):
        tail += comb(n, j - 1)
        # coverage 1 - 2 tail / 2^n >= 95 %  <=>  2 tail * den <= num * 2^n
        if 2 * tail * miss_den <= miss_num * 2**n:
            best = j
        else:
            break
    if best == 0:
        return None
    ordered = sorted(values)
    return ordered[best - 1], ordered[n - best]


def describe(values: Sequence[int]) -> dict[str, int | None]:
    """Count, band (10 %, median, 90 %), range and the median's exact 95 % interval."""
    interval = median_interval(values)
    return {
        "n": len(values),
        "min": min(values),
        "q10": quantile(values, LOW_PERMILLE),
        "median": quantile(values, PERMILLE // 2),
        "q90": quantile(values, HIGH_PERMILLE),
        "max": max(values),
        "ci95_low": interval[0] if interval else None,
        "ci95_high": interval[1] if interval else None,
    }


def paired(a: Mapping[int, int], b: Mapping[int, int]) -> dict[str, int | None]:
    """Compare ``a`` with ``b`` on the seeds both have: ``a[seed] - b[seed]`` per seed."""
    seeds = sorted(set(a) & set(b))
    if not seeds:
        raise ValueError("no shared seeds")
    diffs = [a[s] - b[s] for s in seeds]
    wins = sum(d > 0 for d in diffs)
    ties = sum(d == 0 for d in diffs)
    losses = len(seeds) - wins - ties
    interval = median_interval(diffs)
    return {
        "seeds": len(seeds),
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "median_diff": quantile(diffs, PERMILLE // 2),
        "ci95_low": interval[0] if interval else None,
        "ci95_high": interval[1] if interval else None,
        "superiority_ppm": (2 * wins + ties) * PPM // (2 * len(seeds)),
        "sign_p_more_ppm": sign_p_ppm(wins, losses),
        "sign_p_less_ppm": sign_p_ppm(losses, wins),
    }


def sign_p_ppm(wins: int, losses: int) -> int:
    """One-sided exact sign test: P(at least ``wins`` of the untied seeds | no difference), ppm.

    Ties carry no sign and are dropped, as in the textbook test. Rounded up,
    so a reported p is never smaller than the exact one. No untied seed: 1.
    """
    n = wins + losses
    tail = sum(comb(n, k) for k in range(wins, n + 1))
    return -(-tail * PPM // 2**n)
