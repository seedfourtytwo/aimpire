"""Markdown lab notebook for one finished run (F4c, ADR-0010, ADR-0013 section 8).

Why: each ladder level is done only when its experiment report exists
(ADR-0010). The notebook is that report's raw material: everything needed to
read a run at a glance and to reproduce it, in a file that diffs well in git
and renders on GitHub.

It holds six sections, in order:
    Run        id, seed, rules version and hash, preset and its systems, ticks
    Metrics    first, last, min and max of every recorded metric
    Charts     one Tufte SVG per metric, written next to the notebook, linked
    Ledger     ledger totals by material and kind (entries and net milli-units)
    Outcomes   decision outcome counts in the eight ADR-0013 categories
    Reproduce  the command that reruns the run, as given by the caller

The text has no timestamps or machine paths, so the same run writes the same
bytes. The caller chooses the path, normally ``runs/<run_id>/notebook.md``.
"""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from aimpire.report.charts import line_chart_svg
from aimpire.report.markdown import cell, table
from aimpire.report.metrics import MetricsRecorder
from aimpire.sim.ledger import Ledger
from aimpire.sim.scheduler import Preset

# ADR-0013 section 8: every decision ends in exactly one of these.
OUTCOMES: Final = (
    "VALID",
    "PARTIAL",
    "INVALID",
    "REFUSAL",
    "TRUNCATED",
    "TIMEOUT",
    "PROVIDER_ERROR",
    "BUDGET",
)


@dataclass(frozen=True, slots=True)
class RunInfo:
    """What identifies a run. ``reproduce`` is the exact command that reruns it."""

    run_id: str
    seed: int
    rules_version: str
    rules_hash: str
    preset: Preset
    ticks: int
    reproduce: str


def _chart_file(index: int, name: str) -> str:
    """A safe, unique file name for a metric's chart."""
    slug = re.sub(r"[^a-z0-9_-]+", "-", name.lower()).strip("-") or "metric"
    return f"chart-{index:02d}-{slug}.svg"


def _run_section(info: RunInfo) -> list[str]:
    systems = [
        f"  {i}. `{spec.name}`"
        + (f" {json.dumps(dict(spec.params), sort_keys=True)}" if spec.params else "")
        for i, spec in enumerate(info.preset.systems, start=1)
    ]
    return [
        f"- Run id: `{info.run_id}`",
        f"- Seed: {info.seed}",
        f"- Rules: version `{info.rules_version}`, hash `{info.rules_hash}`",
        f"- Preset: `{info.preset.name}`, systems in order:",
        *(systems or ["  (none)"]),
        f"- Ticks: {info.ticks}",
    ]


def _metrics_section(metrics: MetricsRecorder) -> list[str]:
    if not metrics.rows:
        return ["No metrics recorded."]
    rows: list[tuple[object, ...]] = []
    for name in metrics.names:
        values = metrics.series(name)
        rows.append((name, values[0], values[-1], min(values), max(values)))
    first, last = metrics.ticks()[0], metrics.ticks()[-1]
    return [
        f"Recorded ticks {first} to {last} ({len(metrics.rows)} rows). "
        "Values are milli-units or counts.",
        "",
        *table(("metric", "first", "last", "min", "max"), rows),
    ]


def _charts_section(metrics: MetricsRecorder, folder: Path) -> list[str]:
    if not metrics.rows:
        return ["No metrics recorded."]
    lines: list[str] = []
    ticks = metrics.ticks()
    for index, name in enumerate(metrics.names, start=1):
        file_name = _chart_file(index, name)
        svg = line_chart_svg(ticks, metrics.series(name), label=name)
        (folder / file_name).write_bytes(svg.encode("utf-8"))
        lines.append(f"![{cell(name)}]({file_name})")
        lines.append("")
    return lines[:-1]


def _ledger_section(ledger: Ledger) -> list[str]:
    totals: dict[tuple[str, str], list[int]] = {}
    for entry in ledger.entries:
        count_net = totals.setdefault((entry.material, entry.kind), [0, 0])
        count_net[0] += 1
        count_net[1] += entry.delta
    if not totals:
        return ["No ledger entries."]
    rows: list[tuple[object, ...]] = [
        (material, kind, count, net) for (material, kind), (count, net) in sorted(totals.items())
    ]
    return [
        "Net change in milli-units by material and cause.",
        "",
        *table(("material", "kind", "entries", "net"), rows),
    ]


def _outcomes_section(outcomes: Mapping[str, int]) -> list[str]:
    unknown = sorted(set(outcomes) - set(OUTCOMES))
    if unknown:
        raise ValueError(f"unknown outcome categories {unknown}; expected {OUTCOMES}")
    rows: list[tuple[object, ...]] = [(c, outcomes.get(c, 0)) for c in OUTCOMES]
    note = "Decision outcomes (ADR-0013 section 8)."
    if not any(outcomes.values()):
        note += " No model decisions in this run."
    return [note, "", *table(("outcome", "count"), rows)]


def render_notebook(
    info: RunInfo,
    metrics: MetricsRecorder,
    ledger: Ledger,
    chart_folder: Path,
    outcomes: Mapping[str, int] | None = None,
) -> str:
    """Return the notebook text and write chart SVGs into ``chart_folder``."""
    outcome_lines = _outcomes_section(outcomes or {})
    sections = [
        ("Run", _run_section(info)),
        ("Metrics", _metrics_section(metrics)),
        ("Charts", _charts_section(metrics, chart_folder)),
        ("Ledger", _ledger_section(ledger)),
        ("Outcomes", outcome_lines),
        ("Reproduce", ["```", info.reproduce, "```"]),
    ]
    lines = [f"# Lab notebook: run {info.run_id}"]
    for title, body in sections:
        lines += ["", f"## {title}", "", *body]
    return "\n".join(lines) + "\n"


def write_notebook(
    path: Path,
    info: RunInfo,
    metrics: MetricsRecorder,
    ledger: Ledger,
    outcomes: Mapping[str, int] | None = None,
) -> Path:
    """Write ``path`` (normally ``runs/<run_id>/notebook.md``) and its charts beside it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = render_notebook(info, metrics, ledger, path.parent, outcomes)
    path.write_bytes(text.encode("utf-8"))
    return path
