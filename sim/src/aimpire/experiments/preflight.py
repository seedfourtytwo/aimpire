"""The worst-case cost check made before any call (backlog F6 budget rules).

``aimpire qualify`` and ``aimpire batch`` print the worst case first, then
refuse to start if it could cross what is left: of the run cap for the
costliest single run, and of the monthly cap across every run already booked
this month (``persistence.spend.month_spent`` over the runs folder). The
council barrier still gates each call (``cognition.budget``); this check
makes sure an experiment is not cut short halfway by that gate.

Free work (mock, rule, a local model) has a worst case of 0 and is never
refused, even when the month is spent. Money is integer micro-dollars.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aimpire.cognition.budget import MICRO_USD_PER_USD, Caps
from aimpire.persistence.spend import month_spent

Echo = Callable[[str], None]


def spent_this_month(runs_root: Path, month: str) -> int:
    """Micro-dollars booked in ``month`` by every run under ``runs_root`` (0 if it is new)."""
    return month_spent(runs_root, month) if runs_root.exists() else 0


def usd(micro_usd: int) -> str:
    """Micro-dollars as dollars with six decimals, integer arithmetic only."""
    sign = "-" if micro_usd < 0 else ""
    whole, frac = divmod(abs(micro_usd), MICRO_USD_PER_USD)
    return f"{sign}${whole}.{frac:06d}"


class OverBudget(RuntimeError):  # noqa: N818 (names the refusal, as the message does)
    """The worst case could cross a cap. Raised before any provider is built or called."""

    def __init__(self, worst_case_micro_usd: int, remaining_micro_usd: int, cap: str) -> None:
        self.worst_case_micro_usd = worst_case_micro_usd
        self.remaining_micro_usd = remaining_micro_usd
        super().__init__(
            f"refused: worst case {usd(worst_case_micro_usd)} exceeds the "
            f"{usd(remaining_micro_usd)} left under the {cap} cap"
        )


@dataclass(frozen=True, slots=True)
class CostPlan:
    """Worst cases in micro-dollars: of everything, and of the costliest single run."""

    total_micro_usd: int
    largest_run_micro_usd: int
    run_cap_micro_usd: int


def check_budget(plan: CostPlan, *, runs_root: Path, month: str, echo: Echo) -> None:
    """Print the worst case, then raise ``OverBudget`` if it does not fit what is left."""
    monthly = Caps().monthly_micro_usd
    left_month = max(0, monthly - spent_this_month(runs_root, month))
    echo(
        f"worst-case cost {usd(plan.total_micro_usd)} "
        f"(largest run {usd(plan.largest_run_micro_usd)}); "
        f"left this month {usd(left_month)}, run cap {usd(plan.run_cap_micro_usd)}"
    )
    if plan.total_micro_usd == 0:
        return
    if plan.largest_run_micro_usd > plan.run_cap_micro_usd:
        raise OverBudget(plan.largest_run_micro_usd, plan.run_cap_micro_usd, "per-run")
    if plan.total_micro_usd > left_month:
        raise OverBudget(plan.total_micro_usd, left_month, "monthly")
