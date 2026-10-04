"""Markdown text of one experiment report (backlog F6d, ADR-0014 section 5).

Sections, in order:
    Pre-registration  hypothesis, metrics and the experiment file's hash
    Design            world, timing, seats, paired seeds, replicates, arms
    Results           per arm and mind: lower median and range of each metric
    Charts            usable-reply share per council, one small multiple per group
    Runs              every run: seed, rotation, replicate, seats, final hash, spend

Results are stated as rates under conditions over a stated number of runs,
never as traits (ADR-0014). The data come from ``experiments.report``.
"""

from collections.abc import Mapping
from typing import Any

from aimpire.report.markdown import cell, table

_HASH_SHOWN = 12


def _stat(stats: Mapping[str, int]) -> str:
    return f"{stats['median']} [{stats['min']} to {stats['max']}]"


def _preregistration(exp: Mapping[str, Any]) -> list[str]:
    secondary = ", ".join(exp["secondary_metrics"]) or "none"
    return [
        "## Pre-registration",
        "",
        f"> {cell(exp['hypothesis'])}",
        "",
        f"- Primary metric: `{exp['primary_metric']}`",
        f"- Secondary metrics: {secondary}",
        f"- Experiment file hash (BLAKE2b-256): `{exp['file_hash']}`",
    ]


def _design(exp: Mapping[str, Any], arms: list[dict[str, Any]], runs: int) -> list[str]:
    rows = [
        (a["id"], a["knowledge_arm"], a["renderer"], a["prompt"], ", ".join(a["minds"]))
        for a in arms
    ]
    return [
        "## Design",
        "",
        f"- World `{exp['world']}`: {exp['ticks']} days, a council every "
        f"{exp['council_every']} days, {exp['seats']} seats.",
        f"- Paired seeds (every arm runs each): {', '.join(map(str, exp['seeds']))}.",
        f"- {exp['replicates']} replicates per seed and seat rotation; {runs} runs in all.",
        "- Seats rotate cyclically, so every mind sits in every seat.",
        "",
        *table(("arm", "knowledge", "renderer", "prompt", "minds"), rows),
    ]


def _results(names: list[str], groups: list[dict[str, Any]]) -> list[str]:
    header = ("arm", "mind", "runs", *names)
    rows = [
        (g["arm"], g["mind"], g["runs"], *(_stat(g["metrics"][n]) for n in names)) for g in groups
    ]
    return [
        "## Results",
        "",
        "Shares of decisions in parts per million: lower median [minimum to maximum] over runs.",
        "",
        *table(header, rows),
    ]


def _charts(groups: list[dict[str, Any]]) -> list[str]:
    lines = ["## Charts", "", "Usable replies (valid or partial) per council, permille."]
    for g in groups:
        lines += [
            "",
            f"{cell(g['arm'])}, {cell(g['mind'])}",
            "",
            f"![{cell(g['mind'])}]({g['chart']})",
        ]
    return lines


def _runs(runs: list[dict[str, Any]]) -> list[str]:
    rows = [
        (
            r["run_id"],
            r["seed"],
            r["rotation"],
            r["replicate"],
            ", ".join(f"{civ}={mind}" for civ, mind in sorted(r["seats"].items())),
            r["final_hash"][:_HASH_SHOWN],
            r["charged_micro_usd"],
        )
        for r in runs
    ]
    header = ("run", "seed", "rotation", "replicate", "seats", "final hash", "spent (µ$)")
    return ["## Runs", "", *table(header, rows)]


def experiment_markdown(data: Mapping[str, Any]) -> str:
    """The report text for ``experiments.report.report_data`` output."""
    exp = data["experiment"]
    names = [exp["primary_metric"], *exp["secondary_metrics"]]
    sections = [
        [f"# Experiment {exp['id']}"],
        _preregistration(exp),
        _design(exp, data["arms"], len(data["runs"])),
        _results(names, data["groups"]),
        _charts(data["groups"]),
        _runs(data["runs"]),
    ]
    return "\n\n".join("\n".join(s) for s in sections) + "\n"
