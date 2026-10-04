"""Spending caps for model calls, in integer micro-dollars (ADR-0005, backlog F6 budget rules).

Why integers: a budget is checked many times and summed across runs; float
rounding would let small errors accumulate past a cap. Every amount here is a
whole number of **micro-dollars** (millionths of a US dollar). Prices are
micro-dollars per million tokens, so "$3 per MTok" is ``3_000_000``.

How a call is gated (ADR-0005, "reserve before dispatch, then reconcile"):

1. ``reserve`` before the call, with the provider's worst-case estimate.
   * An estimate of 0 is a known free call (mock, rule, recorded, a local
     Ollama model). It is always granted: free calls are never refused for
     cost, even when every cap is spent.
   * ``None`` means the price is unknown. It is refused (``UNPRICED``) unless
     the guard was built with ``allow_unpriced``: caps fail closed.
   * Otherwise the call is refused if spent + held + estimate would **cross**
     the per-run cap or the monthly cap. Reaching a cap exactly is allowed.
2. The refused call is never made. The barrier records it as a ``BUDGET``
   decision with ``BUDGET_EXHAUSTED``; nothing crashes.
3. ``settle`` after the call releases the reservation and charges the actual
   cost (``Price.cost`` of the reported usage). The gate decides the charge:
   in recorded replay (``RecordedRefusals``) it is always 0, because the
   recorded usage was paid for by the original run.

Reservations happen for every seat of a council, in turn order, before any
call is sent, so which seat is refused under a tight cap is deterministic.

Defaults (creator decision 2026-10-04): 20 dollars a month across all runs,
2 dollars per run. A profile may set less.
"""

from dataclasses import dataclass, field
from enum import StrEnum, unique
from typing import Final, Protocol

from aimpire.cognition.protocol import Usage

MICRO_USD_PER_USD: Final = 1_000_000
TOKENS_PER_MTOK: Final = 1_000_000
DEFAULT_RUN_CAP_MICRO_USD: Final = 2 * MICRO_USD_PER_USD
DEFAULT_MONTHLY_CAP_MICRO_USD: Final = 20 * MICRO_USD_PER_USD


def _check_amount(name: str, value: object) -> None:
    """Amounts are non-negative ints; ``bool`` and ``float`` are refused."""
    if type(value) is not int:
        raise TypeError(f"{name} must be an int number of micro-dollars, got {value!r}")
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")


def _ceil_div(numer: int, denom: int) -> int:
    return -(-numer // denom)


@dataclass(frozen=True, slots=True)
class Price:
    """List price in micro-dollars per million tokens. Reasoning tokens bill as output."""

    input_micro_usd_per_mtok: int
    output_micro_usd_per_mtok: int

    def __post_init__(self) -> None:
        _check_amount("input_micro_usd_per_mtok", self.input_micro_usd_per_mtok)
        _check_amount("output_micro_usd_per_mtok", self.output_micro_usd_per_mtok)

    def _of(self, input_tokens: int, output_tokens: int) -> int:
        total = (
            input_tokens * self.input_micro_usd_per_mtok
            + output_tokens * self.output_micro_usd_per_mtok
        )
        return _ceil_div(total, TOKENS_PER_MTOK)  # rounded up: never under-count spend

    def cost(self, usage: Usage) -> int:
        """Actual cost of a call in micro-dollars, rounded up."""
        return self._of(usage.input_tokens, usage.output_tokens + usage.reasoning_tokens)

    def worst_case(self, input_tokens: int, max_output_tokens: int) -> int:
        """Worst-case cost in micro-dollars: every allowed output token used."""
        return self._of(input_tokens, max_output_tokens)


FREE: Final = Price(0, 0)


@dataclass(frozen=True, slots=True)
class Caps:
    """Spending caps in micro-dollars: per run and per calendar month across all runs."""

    run_micro_usd: int = DEFAULT_RUN_CAP_MICRO_USD
    monthly_micro_usd: int = DEFAULT_MONTHLY_CAP_MICRO_USD

    def __post_init__(self) -> None:
        _check_amount("run_micro_usd", self.run_micro_usd)
        _check_amount("monthly_micro_usd", self.monthly_micro_usd)


@unique
class Refusal(StrEnum):
    """Why a call was not made. Stored with the decision."""

    RUN_CAP = "RUN_CAP"
    MONTHLY_CAP = "MONTHLY_CAP"
    UNPRICED = "UNPRICED"


@dataclass(frozen=True, slots=True)
class Grant:
    """The answer to one reservation. ``refused`` is None when the call may go ahead."""

    decision_id: str
    reserved: int
    refused: Refusal | None


class Gate(Protocol):
    """What the council barrier asks before each call, and tells after it."""

    def reserve(self, decision_id: str, estimate: int | None) -> Grant:
        """Hold ``estimate`` micro-dollars for a call, or refuse it."""
        ...

    def settle(self, grant: Grant, cost: int) -> int:
        """Release the reservation for a call that cost ``cost``; return the amount charged."""
        ...


@dataclass(slots=True)
class BudgetGuard:
    """Live spending guard for one run.

    ``spent_run`` is what this run has already spent (from its run store);
    ``spent_month`` is what all runs, this one included, spent this month.
    """

    caps: Caps
    spent_run: int = 0
    spent_month: int = 0
    allow_unpriced: bool = False
    held: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        _check_amount("spent_run", self.spent_run)
        _check_amount("spent_month", self.spent_month)

    def reserve(self, decision_id: str, estimate: int | None) -> Grant:
        """Grant or refuse a call worth at most ``estimate`` micro-dollars (see module doc)."""
        if type(estimate) is int and estimate == 0:
            return Grant(decision_id, 0, None)
        if type(estimate) is not int or estimate < 0:
            # Unknown, or a provider bug (float, negative): fail closed.
            if self.allow_unpriced and estimate is None:
                return Grant(decision_id, 0, None)
            return Grant(decision_id, 0, Refusal.UNPRICED)
        if self.spent_run + self.held + estimate > self.caps.run_micro_usd:
            return Grant(decision_id, 0, Refusal.RUN_CAP)
        if self.spent_month + self.held + estimate > self.caps.monthly_micro_usd:
            return Grant(decision_id, 0, Refusal.MONTHLY_CAP)
        self.held += estimate
        return Grant(decision_id, estimate, None)

    def settle(self, grant: Grant, cost: int) -> int:
        """Replace the reservation with the actual cost, and charge it."""
        _check_amount("cost", cost)
        self.held -= grant.reserved
        self.spent_run += cost
        self.spent_month += cost
        return cost


@dataclass(frozen=True, slots=True)
class RecordedRefusals:
    """The gate for recorded replay: refuses exactly what the original run refused.

    Replay costs nothing, so nothing is reserved or charged. The refusals come
    from the original run's inputs log, so a ``BUDGET`` decision replays as
    ``BUDGET`` and the replayed state matches.
    """

    refusals: dict[str, Refusal]

    def reserve(self, decision_id: str, estimate: int | None) -> Grant:
        """Refuse a decision the original run refused; grant the rest for free."""
        return Grant(decision_id, 0, self.refusals.get(decision_id))

    def settle(self, grant: Grant, cost: int) -> int:
        """Replay is free: the original run already paid. Nothing is charged."""
        return 0
