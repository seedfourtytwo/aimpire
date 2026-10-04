"""Gather a finished batch into one report: JSON data, Markdown text, small-multiple charts.

Why grouped by arm and mind: the unit of comparison is the mind under one
condition, measured over every seed, rotation and replicate (ADR-0014). For
each group the report gives the lower median, minimum and maximum of every
pre-registered metric across runs, and one chart of the usable-reply share
per council (``report.charts``; same size for every group, so they read as
small multiples).

Everything is integer and sorted, and nothing holds a clock or a machine
path, so the same batch writes the same bytes.
"""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from aimpire.experiments.experiment import Experiment
from aimpire.experiments.summary import (
    PERMILLE,
    USABLE,
    RunSummary,
    lower_median,
)
from aimpire.report.charts import line_chart_svg
from aimpire.report.experiment import experiment_markdown


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def chart_name(arm: str, mind: str) -> str:
    """The chart file of one group, relative to the report folder."""
    return f"charts/{arm}--{_slug(mind)}.svg"


def _per_council(runs: Sequence[RunSummary], mind: str) -> tuple[list[int], list[int]]:
    """Councils, and the permille of ``mind``'s decisions at each that were usable."""
    by_council: dict[int, list[str]] = {}
    for run in runs:
        for council, m, outcome in run.decisions:
            if m == mind:
                by_council.setdefault(council, []).append(outcome)
    councils = sorted(by_council)
    shares = [
        sum(o in USABLE for o in by_council[c]) * PERMILLE // len(by_council[c]) for c in councils
    ]
    return councils, shares


def _group(exp: Experiment, arm: str, mind: str, runs: Sequence[RunSummary]) -> dict[str, Any]:
    seated = [r for r in runs if r.arm == arm and mind in r.minds()]
    names = (exp.primary_metric, *exp.secondary_metrics)
    stats: dict[str, dict[str, int]] = {}
    for name in names:
        values = [r.metrics(mind)[name] for r in seated]
        stats[name] = {"median": lower_median(values), "min": min(values), "max": max(values)}
    councils, shares = _per_council(seated, mind)
    return {
        "arm": arm,
        "mind": mind,
        "runs": len(seated),
        "metrics": stats,
        "per_council": {"councils": councils, "usable_permille": shares},
        "chart": chart_name(arm, mind),
    }


def _run(run: RunSummary) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "arm": run.arm,
        "seed": run.seed,
        "rotation": run.rotation,
        "replicate": run.replicate,
        "seats": dict(run.seats),
        "final_hash": run.final_hash,
        "charged_micro_usd": run.charged_micro_usd,
        "metrics": {mind: run.metrics(mind) for mind in run.minds()},
    }


def report_data(exp: Experiment, runs: Sequence[RunSummary]) -> dict[str, Any]:
    """The whole report as plain JSON-ready data."""
    return {
        "experiment": {
            "id": exp.id,
            "file_hash": exp.file_hash,
            "hypothesis": exp.hypothesis,
            "primary_metric": exp.primary_metric,
            "secondary_metrics": list(exp.secondary_metrics),
            "world": exp.world,
            "ticks": exp.ticks,
            "council_every": exp.council_every,
            "seats": exp.seats,
            "seeds": list(exp.seeds),
            "replicates": exp.replicates,
        },
        "arms": [
            {
                "id": a.id,
                "knowledge_arm": a.knowledge_arm,
                "renderer": a.renderer,
                "prompt": a.prompt,
                "prompt_hash": a.prompt_hash,
                "minds": [m.label for m in a.models],
            }
            for a in exp.arms
        ],
        "groups": [_group(exp, a.id, m.label, runs) for a in exp.arms for m in a.models],
        "runs": [_run(r) for r in runs],
    }


def write_experiment_report(
    exp: Experiment, runs: Sequence[RunSummary], out_dir: Path
) -> tuple[Path, Path]:
    """Write ``report.md``, ``report.json`` and ``charts/*.svg``; return the two report paths."""
    data = report_data(exp, runs)
    (out_dir / "charts").mkdir(parents=True, exist_ok=True)
    for group in data["groups"]:
        series = group["per_council"]
        if series["councils"]:
            svg = line_chart_svg(series["councils"], series["usable_permille"], group["mind"])
            (out_dir / group["chart"]).write_text(svg, encoding="utf-8")
    md, js = out_dir / "report.md", out_dir / "report.json"
    md.write_text(experiment_markdown(data), encoding="utf-8")
    js.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return md, js
