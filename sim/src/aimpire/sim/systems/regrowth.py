"""Wild food regrowth: logistic growth plus a seed term (backlog M0a, ADR-0012).

The rule, per tile and per tick, with r and s the per-tick rates:

    dF = r F (K - F) / K + s (K - F) = (K - F)(r F + s K) / K,   never above K.

* ``r F (K - F) / K`` is logistic growth: fast at half the ceiling, slow when
  nearly empty or nearly full.
* ``s (K - F)`` is the seed term: food blown in from the surroundings, so an
  emptied tile restarts (ADR-0012 "no absorbing zero").

Integer method: r and s are rules ``Rate`` values ``(ppm, per_ticks)``. Over
a common period ``L = lcm(r_per, s_per)`` the exact change this tick is

    numerator   = (K - F) * (r_ppm * (L / r_per) * F + s_ppm * (L / s_per) * K)
    denominator = K * PPM * L

and ``fixed.apply_fraction_array`` floors it per tile and carries the
remainder in ``state.carries["food"]`` (units of ``1 / denominator``; part of
the state hash). So no growth is lost to rounding, however small. The rules
loader keeps ``r + s <= 1`` a tick, which makes the floored change at most
``K - F``; the clamp below only guards that bound. A tile with ``K = 0``
does not grow.

Steady state under a constant harvest fraction: yield ``K (1 - x)(r x + s)``,
largest at ``x* = (1 - s/r) / 2`` (the acceptance tests check this).
"""

import math
from dataclasses import dataclass, field
from typing import Final

import numpy as np

from aimpire.sim.calendar import Rate
from aimpire.sim.fixed import PPM, Int64Array, apply_fraction_array
from aimpire.sim.scheduler import Cadence, TickContext
from aimpire.sim.state import WorldState
from aimpire.sim.world.m0 import CEILING, FOOD

NAME: Final = "regrowth"
KIND: Final = "REGROWTH"
MATERIAL: Final = "food"
"""Ledger material name for standing wild food (the ``food`` layer, mu)."""

_INT64_LIMIT: Final = 2**63


def regrowth_delta(
    food: Int64Array,
    ceiling: Int64Array,
    carries: Int64Array,
    rate: tuple[int, int],
    seed: tuple[int, int],
) -> tuple[Int64Array, Int64Array]:
    """Return ``(delta, new_carries)`` for one tick; ``delta`` is in mu, ``0 <= delta <= K - F``.

    ``rate`` and ``seed`` are ``(ppm, per_ticks)`` from ``Rate.resolve``.
    Raises ``OverflowError`` before any int64 intermediate could wrap.
    """
    (r_ppm, r_per), (s_ppm, s_per) = rate, seed
    period = math.lcm(r_per, s_per)
    r_w, s_w = r_ppm * (period // r_per), s_ppm * (period // s_per)
    k_max = int(ceiling.max()) if ceiling.size else 0
    if k_max * k_max * (r_w + s_w) + k_max * PPM * period >= _INT64_LIMIT:
        raise OverflowError("regrowth numerator would exceed int64")
    growing = ceiling > 0
    gap = np.maximum(ceiling - food, 0)
    numerators = np.where(growing, gap * (np.int64(r_w) * food + np.int64(s_w) * ceiling), 0)
    denominators = np.where(growing, ceiling * np.int64(PPM * period), 1)
    quotients, new_carries = apply_fraction_array(
        numerators.astype(np.int64), denominators.astype(np.int64), carries
    )
    return np.minimum(quotients, gap).astype(np.int64), new_carries


@dataclass(frozen=True, slots=True)
class Regrowth:
    """The regrowth system: every tile at once, independently (not sequential)."""

    rate: Rate
    """Logistic rate r."""
    seed: Rate
    """Seed term s."""
    name: str = field(default=NAME, init=False)
    cadence: Cadence = field(default="tick", init=False)
    sequential: bool = field(default=False, init=False)

    def step(self, state: WorldState, ctx: TickContext) -> None:
        """Grow ``food`` towards ``ceiling``; record the total as one ``REGROWTH`` entry."""
        delta, state.carries[FOOD] = regrowth_delta(
            state.layers[FOOD],
            state.layers[CEILING],
            state.carries[FOOD],
            self.rate.resolve(ctx.calendar),
            self.seed.resolve(ctx.calendar),
        )
        state.layers[FOOD] += delta
        ctx.ledger.record(MATERIAL, int(delta.sum(dtype=np.int64)), KIND, "all tiles")
