"""Markdown text of one experiment report (backlog F6d, M0e; ADR-0014 section 5).

Sections, in order:
    Pre-registration  hypothesis, metrics, the file's hash and the document's
    Design            world, timing, seats, paired seeds, replicates, arms
    Results           per arm and mind: each metric's median, band and exact interval
    Paired            model against each rule baseline, seed by seed (if any)
    Bands             each measure at every checkpoint, one panel per group (if measured)
    Charts            usable-reply share per council, one small multiple per group
    Runs              every run: seed, rotation, replicate, seats, final hash, spend

Results are stated as rates under conditions over a stated number of runs,
never as traits (ADR-0014). The data come from ``experiments.report``.
"""

from collections.abc import Mapping
from typing import Any

from aimpire.report.markdown import cell, table

_HASH_SHOWN = 12


def _interval(stats: Mapping[str, int | None]) -> str:
    low, high = stats["ci95_low"], stats["ci95_high"]
    return "n/a" if low is None or high is None else f"{low} to {high}"


def _stat(stats: Mapping[str, Any]) -> str:
    """``median [q10 to q90] (95 %: low to high)``; the range is in the JSON."""
    return f"{stats['median']} [{stats['q10']} to {stats['q90']}] (95 %: {_interval(stats)})"


def _preregistration(exp: Mapping[str, Any]) -> list[str]:
    secondary = ", ".join(exp["secondary_metrics"]) or "none"
    lines = [
        "## Pre-registration",
        "",
        f"> {cell(exp['hypothesis'])}",
        "",
        f"- Primary metric: `{exp['primary_metric']}`",
        f"- Secondary metrics: {secondary}",
        f"- Experiment file hash (BLAKE2b-256): `{exp['file_hash']}`",
    ]
    if exp.get("preregistration"):
        lines.append(
            f"- Pre-registration `{exp['preregistration']}` hash (BLAKE2b-256): "
            f"`{exp['preregistration_hash']}`"
        )
    return lines


def _design(exp: Mapping[str, Any], arms: list[dict[str, Any]], runs: int) -> list[str]:
    rows = [
        (
            a["id"],
            a["knowledge_arm"],
            a["renderer"],
            a.get("rules", "hidden"),
            a["prompt"],
            ", ".join(a["minds"]),
        )
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
        *table(("arm", "knowledge", "renderer", "rules", "prompt", "minds"), rows),
    ]


def _results(names: list[str], groups: list[dict[str, Any]]) -> list[str]:
    header = ("arm", "mind", "runs", *names)
    rows = [
        (g["arm"], g["mind"], g["runs"], *(_stat(g["metrics"][n]) for n in names)) for g in groups
    ]
    return [
        "## Results",
        "",
        "Over runs: lower median [10th to 90th percentile] (exact 95 % interval of the median, "
        "from order statistics; n/a below 6 runs). Shares are in parts per million, food in "
        "milli-units. Minimum and maximum are in `report.json`.",
        "",
        *table(header, rows),
    ]


_PAIR_STATS = ("seeds", "A more / same / B more", "median A - B", "95 % interval",
               "superiority (ppm)", "sign p, A > B (ppm)", "sign p, A < B (ppm)")  # fmt: skip


def _pair_cells(p: Mapping[str, Any]) -> tuple[object, ...]:
    return (
        p["seeds"],
        f"{p['wins']} / {p['ties']} / {p['losses']}",
        p["median_diff"],
        _interval(p),
        p["superiority_ppm"],
        p["sign_p_more_ppm"],
        p["sign_p_less_ppm"],
    )


def _paired(pairs: list[dict[str, Any]], arm_pairs: list[dict[str, Any]]) -> list[str]:
    if not pairs and not arm_pairs:
        return []
    metric = (pairs or arm_pairs)[0]["metric"]
    lines = [
        "## Paired comparisons",
        "",
        f"`{metric}` seed by seed: per seed, the lower median over a group's runs. "
        "Superiority is P(A > B) + ½ P(tie), in ppm; the sign-test p-values are exact and "
        "one-sided, ties dropped.",
    ]
    if pairs:
        rows = [
            (f"{p['arm']} {p['mind']}", f"{p['baseline_arm']} {p['baseline']}", *_pair_cells(p))
            for p in pairs
        ]
        lines += ["", "Against the rule baselines:", "", *table(("A", "B", *_PAIR_STATS), rows)]
    if arm_pairs:
        rows = [(p["mind"], p["arm_a"], p["arm_b"], *_pair_cells(p)) for p in arm_pairs]
        header = ("mind", "A (arm)", "B (arm)", *_PAIR_STATS)
        lines += ["", "The same mind across arms:", "", *table(header, rows)]
    return lines


def _bands(charts: list[str]) -> list[str]:
    if not charts:
        return []
    lines = [
        "## Bands",
        "",
        "Each measure at every checkpoint: grey from the 10th to the 90th percentile over runs, "
        "the line is the median. One panel per group, the same scales throughout.",
    ]
    for chart in charts:
        name = chart.rsplit("--", 1)[-1].removesuffix(".svg")
        lines += ["", f"**{name}**", "", f"![{name}]({chart})"]
    return lines


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
        _paired(data.get("paired", []), data.get("arm_pairs", [])),
        _bands(data.get("band_charts", [])),
        _charts(data["groups"]),
        _runs(data["runs"]),
    ]
    return "\n\n".join("\n".join(s) for s in sections if s) + "\n"
