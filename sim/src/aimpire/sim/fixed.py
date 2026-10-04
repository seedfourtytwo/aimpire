"""Integer fixed-point helpers for authoritative state (ADR-0012 section A).

Why this module exists: plain floor division on small rates silently stops
changing a quantity. A 1,000 ppm per-tick decay of a value below 1,000 floors to
zero forever, and at 120 ticks a year any yearly rate under 12% is below 1
permille per tick. Every rate in ``aimpire.sim`` therefore goes through these
helpers instead of a bare ``//``.

Units:
    * quantities are non-negative integers in milli-units;
    * rates and chances are integers in parts per million (``PPM``);
    * a rate applies linearly over ``per_ticks`` ticks (ADR-0011 converts
      "per year" or "per season" into ``per_ticks``).

Three tools, one per kind of update:
    * ``apply_rate``: deterministic flows (decay, regrowth, metabolism). Exact:
      the running total of deltas always equals the floor of the exact rational
      total, because the remainder is carried in state. ``apply_fraction_array``
      is its per-tile form, for flows whose denominator differs by tile.
    * ``chance_ppm``: per-entity yes/no events driven by a counter draw.
    * ``stochastic_round``: split a remainder fairly with a counter draw.

Sign rule: every helper rejects negative inputs. Debts and deficits are stored
as separate non-negative quantities.
"""

from typing import Final

import numpy as np
import numpy.typing as npt

PPM: Final = 1_000_000
"""Parts per million: the unit of every rate and chance."""

_INT64_LIMIT: Final = 2**63
U64_MASK: Final = 2**64 - 1

Int64Array = npt.NDArray[np.int64]


def _check_rate_args(ppm: int, per_ticks: int) -> None:
    if ppm < 0:
        raise ValueError(f"rate must be >= 0 ppm, got {ppm}")
    if per_ticks < 1:
        raise ValueError(f"per_ticks must be >= 1, got {per_ticks}")


def apply_rate(value: int, ppm: int, per_ticks: int, carry: int) -> tuple[int, int]:
    """Return ``(delta, new_carry)`` for one tick of a rate applied to ``value``.

    ``delta`` is the whole milli-units to add or remove this tick; the caller
    decides the direction. ``carry`` is the remainder from previous ticks, in
    units of ``1 / (PPM * per_ticks)`` milli-units, and must be stored in state
    beside the quantity (it is part of the state hash).

    Exact: summed over ticks, the deltas equal the floor of
    ``value * ppm * ticks / (PPM * per_ticks)`` while ``value`` is unchanged, so
    no rate ever rounds to zero.
    """
    _check_rate_args(ppm, per_ticks)
    if value < 0:
        raise ValueError(f"value must be >= 0, got {value}")
    denom = PPM * per_ticks
    if not 0 <= carry < denom:
        raise ValueError(f"carry must be in [0, {denom}), got {carry}")
    delta, new_carry = divmod(value * ppm + carry, denom)
    return delta, new_carry


def apply_rate_array(
    values: Int64Array, ppm: int, per_ticks: int, carries: Int64Array
) -> tuple[Int64Array, Int64Array]:
    """Vectorised ``apply_rate`` for an ``int64`` tile layer and its carry layer.

    Raises ``OverflowError`` rather than wrapping: numpy ``int64`` arithmetic
    overflows silently, so the largest intermediate is checked first.
    """
    _check_rate_args(ppm, per_ticks)
    if values.dtype != np.int64 or carries.dtype != np.int64:
        raise TypeError("values and carries must be numpy int64 arrays")
    if values.shape != carries.shape:
        raise ValueError(f"shape mismatch: {values.shape} vs {carries.shape}")
    denom = PPM * per_ticks
    if values.size == 0:
        return values.copy(), carries.copy()
    if int(values.min()) < 0:
        raise ValueError("values must be >= 0")
    if int(carries.min()) < 0 or int(carries.max()) >= denom:
        raise ValueError(f"carries must be in [0, {denom})")
    if int(values.max()) * ppm + denom >= _INT64_LIMIT:
        raise OverflowError("value * ppm + PPM * per_ticks would exceed int64")
    deltas, new_carries = np.divmod(values * np.int64(ppm) + carries, np.int64(denom))
    return deltas.astype(np.int64), new_carries.astype(np.int64)


def apply_fraction_array(
    numerators: Int64Array, denominators: Int64Array, carries: Int64Array
) -> tuple[Int64Array, Int64Array]:
    """Per-tile ``apply_rate``: ``divmod(numerator + carry, denominator)`` element-wise.

    Why: a flow whose rate depends on the tile itself (logistic regrowth uses
    ``F (K - F) / K``) has a different exact denominator on every tile. The
    caller builds the exact numerator and denominator of this tick's change;
    this helper floors it and carries the remainder, so nothing rounds away.
    Each carry is in units of ``1 / denominator`` of its own tile and must
    lie in ``[0, denominator)``.

    The caller must check its numerators for overflow before building them
    (numpy ``int64`` wraps silently); this helper checks only the final sum.
    """
    arrays = (numerators, denominators, carries)
    if any(a.dtype != np.int64 for a in arrays):
        raise TypeError("numerators, denominators and carries must be numpy int64 arrays")
    if not numerators.shape == denominators.shape == carries.shape:
        raise ValueError("numerators, denominators and carries must have one shape")
    if numerators.size == 0:
        return numerators.copy(), carries.copy()
    if int(numerators.min()) < 0 or int(carries.min()) < 0:
        raise ValueError("numerators and carries must be >= 0")
    if int(denominators.min()) < 1:
        raise ValueError("denominators must be >= 1")
    if bool(np.any(carries >= denominators)):
        raise ValueError("every carry must be below its denominator")
    if int(numerators.max()) + int(denominators.max()) >= _INT64_LIMIT:
        raise OverflowError("numerator + carry would exceed int64")
    quotients, new_carries = np.divmod(numerators + carries, denominators)
    return quotients.astype(np.int64), new_carries.astype(np.int64)


def chance_ppm(u: int, ppm: int) -> bool:
    """True with probability ``ppm / PPM`` for a uniform 64-bit draw ``u``.

    ``u`` comes from ``aimpire.sim.rng``. The modulo bias of reducing a 64-bit
    value by one million is about 5e-14, far below any test tolerance.
    """
    if not 0 <= ppm <= PPM:
        raise ValueError(f"ppm must be in [0, {PPM}], got {ppm}")
    if not 0 <= u <= U64_MASK:
        raise ValueError("u must be an unsigned 64-bit draw")
    return (u % PPM) < ppm


def stochastic_round(numer: int, denom: int, u: int) -> int:
    """Return ``floor(numer / denom)``, plus one with probability ``remainder / denom``.

    Unbiased: the expected result equals ``numer / denom`` exactly. Used to split
    a remainder fairly, for example yield shared between foragers.
    """
    if numer < 0:
        raise ValueError(f"numer must be >= 0, got {numer}")
    if denom < 1:
        raise ValueError(f"denom must be >= 1, got {denom}")
    if not 0 <= u <= U64_MASK:
        raise ValueError("u must be an unsigned 64-bit draw")
    quotient, remainder = divmod(numer, denom)
    return quotient + (1 if (u % denom) < remainder else 0)
