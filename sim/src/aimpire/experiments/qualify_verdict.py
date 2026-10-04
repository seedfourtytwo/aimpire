"""Qualification arithmetic: measure the settled councils, judge them against the marks.

Kept apart from the runner so the numbers can be checked without a provider.
All values are integers: counts, parts per million, milliseconds and
micro-dollars. A rate with a zero denominator is ``None`` ("no value"), and a
mark judged on no value fails, so a mind cannot pass by proposing nothing.
"""

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, Final, Literal

from aimpire.cognition.council import Settled
from aimpire.experiments.qualify_data import Cases, Thresholds
from aimpire.experiments.summary import PPM, lower_median
from aimpire.sim.actions import Outcome


def rate_ppm(numerator: int, denominator: int) -> int | None:
    """``numerator / denominator`` in ppm, rounded down; None when the denominator is 0."""
    return numerator * PPM // denominator if denominator else None


@dataclass(frozen=True, slots=True)
class QualifyMetrics:
    """What one mind did on the case set. ``outcomes`` lists only outcomes that occurred."""

    cases: int
    parseable: int
    orders_proposed: int
    orders_accepted: int
    outcomes: dict[str, int]
    latency_p50_ms: int
    latency_max_ms: int
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    priced_cost_micro_usd: int
    reported_cost_micro_usd: int | None

    @property
    def schema_adherence_ppm(self) -> int | None:
        """Replies that parse as a ``MindReply``, per million cases."""
        return rate_ppm(self.parseable, self.cases)

    @property
    def order_validity_ppm(self) -> int | None:
        """Accepted orders per million proposed in parseable replies."""
        return rate_ppm(self.orders_accepted, self.orders_proposed)

    def to_value(self) -> dict[str, Any]:
        """JSON-ready form, rates included."""
        value = asdict(self)
        value["schema_adherence_ppm"] = self.schema_adherence_ppm
        value["order_validity_ppm"] = self.order_validity_ppm
        return value


def _orders_proposed(item: Settled) -> int:
    """How many orders the reply listed (0 when there is no parsed reply)."""
    parsed = item.result.parsed if item.result is not None else None
    orders = parsed.get("orders") if parsed is not None else None
    return len(orders) if isinstance(orders, list) else 0  # pyright: ignore[reportUnknownArgumentType]


def measure(settled: Sequence[Settled]) -> QualifyMetrics:
    """Count the outcomes, orders, tokens, latency and cost of the settled councils."""
    results = [s.result for s in settled if s.result is not None]
    ok = [s for s in settled if s.result is not None and s.result.status == "ok"]
    counts = {o.value: sum(s.record.outcome is o for s in settled) for o in Outcome}
    latencies = [r.latency_ms for r in results] or [0]
    reported = [r.reported_cost_micro_usd for r in results if r.reported_cost_micro_usd is not None]
    return QualifyMetrics(
        cases=len(settled),
        parseable=len(ok),
        orders_proposed=sum(_orders_proposed(s) for s in ok),
        orders_accepted=sum(len(s.record.orders) for s in ok),
        outcomes={name: n for name, n in counts.items() if n},
        latency_p50_ms=lower_median(latencies),
        latency_max_ms=max(latencies),
        input_tokens=sum(r.usage.input_tokens for r in results),
        output_tokens=sum(r.usage.output_tokens for r in results),
        reasoning_tokens=sum(r.usage.reasoning_tokens for r in results),
        priced_cost_micro_usd=sum(s.charged for s in settled),
        reported_cost_micro_usd=sum(reported) if reported else None,
    )


Bound = Literal["min", "max"]


@dataclass(frozen=True, slots=True)
class Check:
    """One mark: the measured value, the limit, and whether the value is at or past it."""

    name: str
    value: int | None
    bound: Bound
    limit: int
    passed: bool


def _check(name: str, value: int | None, bound: Bound, limit: int) -> Check:
    if value is None:
        return Check(name, value, bound, limit, passed=False)
    passed = value >= limit if bound == "min" else value <= limit
    return Check(name, value, bound, limit, passed)


def judge(m: QualifyMetrics, t: Thresholds) -> tuple[Check, ...]:
    """Every mark of ``t`` applied to ``m``, in a fixed order."""
    return (
        _check("schema_adherence_ppm", m.schema_adherence_ppm, "min", t.min_schema_adherence_ppm),
        _check("order_validity_ppm", m.order_validity_ppm, "min", t.min_order_validity_ppm),
        _check("latency_p50_ms", m.latency_p50_ms, "max", t.max_latency_p50_ms),
        _check("latency_max_ms", m.latency_max_ms, "max", t.max_latency_max_ms),
    )


REPORT_VERSION: Final = "qualify-report-v1"


def verdict_data(  # noqa: PLR0913 (the parts of one report)
    *,
    run_id: str,
    mind: str,
    cases: Cases,
    thresholds: Thresholds,
    metrics: QualifyMetrics,
    checks: Sequence[Check],
) -> dict[str, Any]:
    """The JSON report: inputs by version and hash, metrics, checks and the verdict."""
    return {
        "report": REPORT_VERSION,
        "run_id": run_id,
        "mind": mind,
        "cases": {
            "version": cases.version,
            "file_hash": cases.file_hash,
            "count": len(cases.cases),
        },
        "thresholds": asdict(thresholds),
        "metrics": metrics.to_value(),
        "checks": [asdict(c) for c in checks],
        "passed": all(c.passed for c in checks),
    }
