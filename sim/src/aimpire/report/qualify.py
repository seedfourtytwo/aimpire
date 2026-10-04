"""Markdown text of one qualification report (backlog F6c).

Sections: the verdict and its marks, the measured rates, tokens and cost,
the outcome counts (ADR-0013), and the inputs by version and hash so the
report can be reproduced. Rates are shown in parts per million and as a
percentage with one decimal, both from integer arithmetic.
"""

from collections.abc import Mapping
from typing import Any

from aimpire.report.markdown import table

_NO_VALUE = "no value"


def _ppm(value: int | None) -> str:
    """``812500 ppm (81.2%)``, rounded down; ``no value`` for a rate with no denominator."""
    if value is None:
        return _NO_VALUE
    return f"{value} ppm ({value // 10_000}.{value % 10_000 // 1_000}%)"


def _show(name: str, value: int | None) -> str:
    return _ppm(value) if name.endswith("_ppm") else _NO_VALUE if value is None else f"{value} ms"


def _checks(checks: list[dict[str, Any]]) -> list[str]:
    rows = [
        (
            c["name"],
            _show(c["name"], c["value"]),
            f"{'at least' if c['bound'] == 'min' else 'at most'} {c['limit']}",
            "pass" if c["passed"] else "FAIL",
        )
        for c in checks
    ]
    return table(("check", "measured", "mark", "result"), rows)


def _measures(m: Mapping[str, Any]) -> list[str]:
    reported = m["reported_cost_micro_usd"]
    rows = [
        ("cases", m["cases"]),
        ("parseable replies", m["parseable"]),
        ("orders proposed / accepted", f"{m['orders_proposed']} / {m['orders_accepted']}"),
        ("latency median / max (ms)", f"{m['latency_p50_ms']} / {m['latency_max_ms']}"),
        (
            "tokens in / out / reasoning",
            f"{m['input_tokens']} / {m['output_tokens']} / {m['reasoning_tokens']}",
        ),
        ("cost at profile price (µ$)", m["priced_cost_micro_usd"]),
        ("cost reported by provider (µ$)", "not reported" if reported is None else reported),
    ]
    return table(("measure", "value"), rows)


def qualify_markdown(data: Mapping[str, Any]) -> str:
    """The report text for ``experiments.qualify_verdict.verdict_data`` output."""
    m, cases, marks = data["metrics"], data["cases"], data["thresholds"]
    verdict = "PASS" if data["passed"] else "FAIL"
    outcomes = table(("outcome", "count"), sorted(m["outcomes"].items()))
    sections = [
        [f"# Qualification: {data['mind']}", "", f"**{verdict}** against `{marks['version']}`."],
        ["## Checks", "", *_checks(data["checks"])],
        ["## Measures", "", *_measures(m)],
        ["## Outcomes", "", *outcomes],
        [
            "## Inputs",
            "",
            f"- Cases `{cases['version']}`: {cases['count']} observations, "
            f"BLAKE2b-256 `{cases['file_hash']}`.",
            f"- Run store `{data['run_id']}`.",
        ],
    ]
    return "\n\n".join("\n".join(s) for s in sections) + "\n"
