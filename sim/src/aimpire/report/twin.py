"""The twin report: Markdown, JSON data and SVG charts of one Lab twin (ADR-0020, LAB1).

Sections of ``twin.md``, in order:
    Exploratory     the ADR-0014 reminder: a Lab finding is not yet evidence
    Design          world, mind, seeds, length, overrides, tags, rules hashes
    Physics         each W0 law of the variant: ppm, x Earth, change, beyond-model
    First divergence  per seed: first tick, the part(s) first hit, later parts
    End of run      per metric at the last tick: medians and the paired difference
    Metrics         per metric: small multiples per seed, then variant minus baseline
    Runs            every run: seed, side, run id, final hash, spend

Everything is a pure function of the twin's results, with no paths, clock or
host in it, so the same twin writes the same bytes (``test_twin_report_is_reproducible``).
Food is shown in whole food units (one feeds a person for a tick), rounded
half away from zero; the harvest rate stays in milli-units (mu).
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from aimpire.report.bands import band, lower_median, paired_differences, quantile
from aimpire.report.markdown import cell, table
from aimpire.report.twin_charts import paired_difference_svg, small_multiples_svg

_HASH_SHOWN: Final = 12
REMINDER: Final = (
    "Lab runs are exploratory (ADR-0020). A finding here becomes evidence only "
    "through a pre-registered re-run on fresh seeds (ADR-0014)."
)


@dataclass(frozen=True, slots=True)
class MetricView:
    """How one metric is shown: title, unit and the divisor from stored units."""

    title: str
    unit: str
    divisor: int = 1


METRIC_VIEWS: Final[Mapping[str, MetricView]] = {
    "population": MetricView("population", "people"),
    "stores_mu": MetricView("stores", "food units", 1000),
    "near_camp_mu": MetricView("wild food near camp", "food units", 1000),
    "deaths": MetricView("deaths since tick 0", "people"),
    "harvest_per_forager_tick_mu": MetricView(
        "harvest per forager-tick, trailing season", "mu per forager-tick"
    ),
}


def display(value: int, divisor: int) -> int:
    """``value / divisor`` rounded half away from zero, integers only."""
    sign = -1 if value < 0 else 1
    return sign * ((abs(value) + divisor // 2) // divisor)


@dataclass(frozen=True, slots=True)
class MetricSeries:
    """One metric across the twin: per seed (in seed order), both sides, stored units."""

    name: str
    seeds: tuple[int, ...]
    baseline: tuple[tuple[int, ...], ...]
    variant: tuple[tuple[int, ...], ...]

    def shown(self) -> tuple[list[list[int]], list[list[int]]]:
        """Both sides in display units."""
        d = METRIC_VIEWS[self.name].divisor
        return (
            [[display(v, d) for v in s] for s in self.baseline],
            [[display(v, d) for v in s] for s in self.variant],
        )


def end_summary(series: MetricSeries) -> dict[str, Any]:
    """At the last tick, display units: medians of each side and the paired difference."""
    base, var = series.shown()
    last_b, last_v = [s[-1] for s in base], [s[-1] for s in var]
    diffs = [v - b for b, v in zip(last_b, last_v, strict=True)]
    return {
        "metric": series.name,
        "unit": METRIC_VIEWS[series.name].unit,
        "baseline_median": lower_median(last_b),
        "variant_median": lower_median(last_v),
        "diff_median": lower_median(diffs),
        "diff_p10": quantile(diffs, 10),
        "diff_p90": quantile(diffs, 90),
    }


def summary_line(row: Mapping[str, Any]) -> str:
    """One console or table line: ``median diff [10 %, 90 %]``."""
    return f"{row['diff_median']:+d} [{row['diff_p10']:+d}, {row['diff_p90']:+d}]"


def write_charts(
    ticks: Sequence[int], metrics: Sequence[MetricSeries], variant_name: str, out: Path
) -> dict[str, tuple[str, str]]:
    """Write ``charts/<metric>.svg`` and ``charts/<metric>-diff.svg``; return relative paths."""
    charts = out / "charts"
    charts.mkdir(parents=True, exist_ok=True)
    paths: dict[str, tuple[str, str]] = {}
    for m in metrics:
        view = METRIC_VIEWS[m.name]
        base, var = m.shown()
        title = f"{view.title} ({view.unit})"
        panels = list(zip(m.seeds, base, var, strict=True))
        multiples = small_multiples_svg(ticks, panels, title, variant_name)
        diff = paired_difference_svg(ticks, band(paired_differences(base, var)), title)
        names = (f"charts/{m.name}.svg", f"charts/{m.name}-diff.svg")
        for name, svg in zip(names, (multiples, diff), strict=True):
            (out / name).write_bytes(svg.encode("utf-8"))
        paths[m.name] = names
    return paths


def _design(data: Mapping[str, Any]) -> list[str]:
    overrides = ", ".join(f"`{k}={v}`" for k, v in data["variant"]["overrides"].items())
    seeds = ", ".join(map(str, data["seeds"]))
    return [
        "## Design",
        "",
        f"- World `{data['world']}`, mind `{data['mind']}`, renderer `{data['renderer']}`, "
        f"a council every {data['council_every']} days.",
        f"- {data['ticks']} days ({data['ticks'] // data['ticks_per_year']} years) "
        f"on seeds {seeds}.",
        "- Baseline: no overrides at all. Variant: "
        f"{overrides or 'no overrides'} (variant `{data['variant']['id']}`).",
        f"- Tags: {', '.join(data['tags'])}.",
        f"- Rules hash: baseline `{data['rules_hash']['baseline'][:_HASH_SHOWN]}`, "
        f"variant `{data['rules_hash']['variant'][:_HASH_SHOWN]}`.",
    ]


def _physics(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    body = [
        (
            r["law"],
            ", ".join(r["reads"]),
            r["ppm"],
            r["times_earth"],
            r["change"],
            "beyond-model" if r["beyond_model"] else "",
        )
        for r in rows
    ]
    return [
        "## Physics of the variant",
        "",
        "Each W0 law at the variant's constants (ppm of Earth). Minds are never told these; "
        "they meet them as experience.",
        "",
        *table(("law", "reads", "ppm", "x Earth", "change", "flag"), body),
    ]


def _divergence(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    body = []
    for r in rows:
        first = r["first_parts"]
        later = ", ".join(f"{p} @{t}" for p, t in r["part_first_ticks"].items() if p not in first)
        tick = "never" if r["first_tick"] is None else r["first_tick"]
        body.append(
            (
                r["seed"],
                tick,
                ", ".join(first) or "-",
                later or "-",
                ", ".join(r["final_parts"]) or "none",
            )
        )
    return [
        "## First divergence",
        "",
        "First tick at which any state part differs (the rules hash in `meta` aside), "
        "the part(s) that differed first, the parts that followed (@ tick), "
        "and those still different at the end.",
        "",
        *table(("seed", "first tick", "first part(s)", "then", "different at end"), body),
    ]


def _end(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    body = [
        (
            METRIC_VIEWS[r["metric"]].title,
            r["unit"],
            r["baseline_median"],
            r["variant_median"],
            summary_line(r),
        )
        for r in rows
    ]
    header = ("metric", "unit", "baseline", "variant", "variant - baseline [10 %, 90 %]")
    return [
        "## End of run",
        "",
        "Lower medians across seeds at the last tick.",
        "",
        *table(header, body),
    ]


def _metrics(charts: Mapping[str, tuple[str, str]]) -> list[str]:
    lines = ["## Metrics", "", "Baseline thin grey, variant in colour; panels share a scale."]
    for name, (multiples, diff) in charts.items():
        title = cell(METRIC_VIEWS[name].title)
        lines += [
            "",
            f"### {title}",
            "",
            f"![{title}]({multiples})",
            "",
            f"![{title}, difference]({diff})",
        ]
    return lines


def _runs(runs: Sequence[Mapping[str, Any]]) -> list[str]:
    body = [
        (r["seed"], r["side"], r["run_id"], r["final_hash"][:_HASH_SHOWN], r["charged_micro_usd"])
        for r in runs
    ]
    return ["## Runs", "", *table(("seed", "side", "run", "final hash", "spent (µ$)"), body)]


def twin_markdown(data: Mapping[str, Any], charts: Mapping[str, tuple[str, str]]) -> str:
    """The report text for the twin ``data`` (the content of ``twin.json``)."""
    sections = [
        [f"# Twin {data['twin_id']}", "", f"> {REMINDER}"],
        _design(data),
        _physics(data["physics"]),
        _divergence(data["divergence"]),
        _end(data["end"]),
        _metrics(charts),
        _runs(data["runs"]),
        ["## Reproduce", "", f"`{cell(data['reproduce'])}`"],
    ]
    return "\n\n".join("\n".join(s) for s in sections) + "\n"


def write_twin_report(
    data: Mapping[str, Any], ticks: Sequence[int], metrics: Sequence[MetricSeries], out: Path
) -> Path:
    """Write ``twin.json``, the charts and ``twin.md`` into ``out``; return the Markdown path.

    ``data`` already holds the ``end`` rows (``end_summary`` of each metric).
    """
    out.mkdir(parents=True, exist_ok=True)
    charts = write_charts(ticks, metrics, "variant", out)
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    (out / "twin.json").write_bytes(text.encode("ascii"))
    path = out / "twin.md"
    path.write_bytes(twin_markdown(data, charts).encode("utf-8"))
    return path
