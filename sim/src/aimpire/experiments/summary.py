"""What one finished run says, per mind: outcome shares by run and by council (ADR-0014 s. 5).

Why outcome shares: every decision ends in exactly one ADR-0013 outcome, and
refusals and failures are counted, never replaced. The metrics an experiment
may pre-register are shares of those outcomes per mind per run, in parts per
million. World metrics (population, stores, stock) join when M0 records them.

Medians are the lower median of the integer values, so reports stay integer.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from aimpire.persistence.store import RunStore

PPM: Final = 1_000_000
PERMILLE: Final = 1000

# Each metric is the share of a mind's decisions whose outcome is in the set.
METRIC_OUTCOMES: Final[Mapping[str, frozenset[str]]] = {
    "valid_share_ppm": frozenset({"VALID"}),
    "usable_share_ppm": frozenset({"VALID", "PARTIAL"}),
    "invalid_share_ppm": frozenset({"INVALID"}),
    "refusal_share_ppm": frozenset({"REFUSAL"}),
    "failure_share_ppm": frozenset({"TRUNCATED", "TIMEOUT", "PROVIDER_ERROR", "BUDGET"}),
}
USABLE: Final = METRIC_OUTCOMES["usable_share_ppm"]


@dataclass(frozen=True, slots=True)
class RunSummary:
    """One run's identity, seat assignment, and every decision as ``(council, mind, outcome)``."""

    run_id: str
    arm: str
    seed: int
    rotation: int
    replicate: int
    seats: tuple[tuple[str, str], ...]
    decisions: tuple[tuple[int, str, str], ...]
    final_hash: str
    charged_micro_usd: int

    def minds(self) -> list[str]:
        """The minds seated in this run, sorted."""
        return sorted({mind for _, mind in self.seats})

    def metrics(self, mind: str) -> dict[str, int]:
        """Every metric for ``mind`` in this run, in ppm of its decisions."""
        outcomes = [o for _, m, o in self.decisions if m == mind]
        return {name: share_ppm(outcomes, wanted) for name, wanted in METRIC_OUTCOMES.items()}


def share_ppm(outcomes: Sequence[str], wanted: frozenset[str]) -> int:
    """Share of ``outcomes`` in ``wanted``, in ppm, rounded down; 0 when there are none."""
    if not outcomes:
        return 0
    return sum(o in wanted for o in outcomes) * PPM // len(outcomes)


def lower_median(values: Sequence[int]) -> int:
    """The lower median: the middle value, or the smaller of the two middle values."""
    if not values:
        raise ValueError("no values")
    return sorted(values)[(len(values) - 1) // 2]


def summarize(store: RunStore) -> RunSummary:
    """Read one batch run's store into a summary."""
    manifest = store.manifest()
    config = manifest["config"]
    seats: dict[str, str] = config["seats"]
    decisions = tuple(
        (int(row["council"]), seats[row["civ_id"]], str(row["outcome"]))
        for row in store.decisions()
    )
    return RunSummary(
        run_id=manifest["run_id"],
        arm=config["arm"],
        seed=manifest["seed"],
        rotation=config["rotation"],
        replicate=config["replicate"],
        seats=tuple(sorted(seats.items())),
        decisions=decisions,
        final_hash=store.checkpoints()[-1][2],
        charged_micro_usd=store.run_spent(),
    )
