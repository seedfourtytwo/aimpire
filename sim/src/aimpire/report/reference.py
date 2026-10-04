"""Markdown page of a reference ensemble (backlog M0d, ADR-0014 sections 1 and 5).

Sections, in order:
    How it was made      file, hash, rules, seeds, timing; the command that remakes it
    The baselines        one line each on what the rule does
    Headline             people alive at the end: band, exact interval, seeds kept
    Bands by year        each measure at every checkpoint: median (10 % to 90 %)
    Charts               one small-multiple SVG per measure, the same scales throughout
    Paired comparisons   baseline against baseline on the same seeds
    Using the bands      how a mind's result is read against them

Numbers are rates under stated conditions over a stated number of seeds
(ADR-0014). The data come from ``experiments.reference.reference_data``.
"""

from collections.abc import Mapping, Sequence
from typing import Any, Final

from aimpire.report.markdown import table

MILLI: Final = 1000
_UNITS: Final = {"stores_mu": MILLI, "near_camp_mu": MILLI}
_TITLES: Final = {
    "population": "People alive",
    "deaths": "Deaths since day 0",
    "stores_mu": "Food in store (units)",
    "near_camp_mu": "Wild food near the camp (units)",
}
_RULES: Final = {
    "rule:random": "random shares of all the people over the places it knows, every council; "
    "never scouts.",
    "rule:greedy": "everyone but one scout forages the place with the most food last seen.",
    "rule:half_full": "forages a place only above half its estimated ceiling, and only the "
    "surplus; needs no regrowth law.",
    "rule:msy": "holds each place at the analytic optimum of the disclosed regrowth law and "
    "takes its steady yield.",
}


def unit(measure: str, value: int) -> int:
    """A measure in the unit the page shows: whole food units for the ``_mu`` measures."""
    return value // _UNITS.get(measure, 1)


def _band(measure: str, low: int, mid: int, high: int) -> str:
    return f"{unit(measure, mid)} ({unit(measure, low)} to {unit(measure, high)})"


def _interval(stats: Mapping[str, int | None]) -> str:
    low, high = stats["ci95_low"], stats["ci95_high"]
    return "too few seeds" if low is None or high is None else f"{low} to {high}"


def _made(ref: Mapping[str, Any], year: int) -> list[str]:
    seeds = ref["seeds"]
    span = f"{seeds[0]} to {seeds[-1]}" if seeds == list(range(seeds[0], seeds[-1] + 1)) else ""
    return [
        "## How it was made",
        "",
        f"- File `experiments/{ref['id']}.yaml`, BLAKE2b-256 `{ref['file_hash']}`.",
        f"- World `{ref['world']}`, rules `{ref['rules_version']}` (hash "
        f"`{ref['rules_hash'][:16]}`).",
        f"- {len(seeds)} world seeds ({span or 'listed in the JSON'}), one tribe of one seat, "
        f"{ref['ticks']} days ({ref['ticks'] // year} years of {year} days), a council every "
        f"{ref['council_every']} days.",
        "- One run per baseline and seed. Rule baselines are deterministic (the same seed gives "
        "the same run, byte for byte), so replicates would repeat the same numbers.",
        f"- Every number here, and each run's final state hash, is in "
        f"[`{ref['id']}.json`]({ref['id']}.json) beside this page.",
        "",
        "Remake it from the `sim/` folder (free; about a quarter of an hour on two cores):",
        "",
        "```bash",
        f"uv run aimpire batch ../experiments/{ref['id']}.yaml --out ../docs/experiments --jobs 2",
        "```",
    ]


def _baselines(minds: Sequence[Mapping[str, Any]]) -> list[str]:
    lines = ["## The baselines", ""]
    lines += [f"- `{m['mind']}`: {_RULES.get(m['mind'], 'a rule baseline.')}" for m in minds]
    lines += [
        "",
        "All four read only their observation and the disclosed rule, ration in full, and never "
        "move camp.",
    ]
    return lines


def _headline(minds: Sequence[Mapping[str, Any]], years: int) -> list[str]:
    rows = []
    for m in minds:
        pop, deaths = m["final"]["population"], m["final"]["deaths"]
        kept = m["survival"]
        rows.append(
            (
                f"`{m['mind']}`",
                f"{kept['kept_90pct']} of {kept['seeds']}",
                f"{pop['median']} ({pop['q10']} to {pop['q90']})",
                _interval(pop),
                f"{deaths['median']} ({deaths['q10']} to {deaths['q90']})",
            )
        )
    header = (
        "baseline",
        "seeds with ≥ 90 % alive",
        "alive: median (10 to 90 %)",
        "95 % interval of the median",
        "deaths: median (10 to 90 %)",
    )
    return [
        f"## Headline: people alive after {years} years",
        "",
        "Medians are lower medians; the interval is exact (order statistics), not a normal "
        "approximation.",
        "",
        *table(header, rows),
    ]


def _by_year(data: Mapping[str, Any], year: int) -> list[str]:
    ticks = data["checkpoints"]
    lines = ["## Bands by year", "", "Median (10th to 90th percentile) over seeds."]
    for measure in data["measures"]:
        rows = []
        for m in data["minds"]:
            band = m["bands"][measure]
            cells = [
                _band(measure, lo, mid, hi)
                for lo, mid, hi in zip(band["q10"], band["median"], band["q90"], strict=True)
            ]
            rows.append((f"`{m['mind']}`", *cells))
        header = ("baseline", *(f"year {t // year}" for t in ticks))
        lines += ["", f"### {_TITLES.get(measure, measure)}", "", *table(header, rows)]
    return lines


def _charts(data: Mapping[str, Any]) -> list[str]:
    lines = [
        "## Charts",
        "",
        "One panel per baseline, the same scales in every panel: the grey band runs from the "
        "10th to the 90th percentile over seeds, the line is the median, and its last value is "
        "written at its end.",
    ]
    for measure, chart in zip(data["measures"], data["charts"], strict=True):
        title = _TITLES.get(measure, measure)
        lines += ["", f"**{title}**", "", f"![{title}]({chart})"]
    return lines


def _p(ppm: int) -> str:
    """A p-value in ppm as text: tiny ones as a bound, so no float rounding hides them."""
    return "< 0.0001" if ppm < 100 else f"{ppm / 1_000_000:.4f}"


def _paired(pairs: Sequence[Mapping[str, Any]]) -> list[str]:
    rows = [
        (
            f"`{p['a']}` vs `{p['b']}`",
            p["seeds"],
            f"{p['wins']} / {p['ties']} / {p['losses']}",
            p["median_diff"],
            _interval(p),
            f"{p['superiority_ppm'] / 10_000:.1f} %",
            _p(p["sign_p_more_ppm"]),
            _p(p["sign_p_less_ppm"]),
        )
        for p in pairs
    ]
    header = ("pair (A vs B)", "seeds", "A more / same / B more", "median A - B", "95 % interval",
              "P(A > B) + ½ P(tie)", "sign p, A > B", "sign p, A < B")  # fmt: skip
    return [
        "## Paired comparisons",
        "",
        "People alive at the end, compared seed by seed on the same worlds (the seed is the unit "
        "of analysis, ADR-0014). The sign-test p-values are exact and one-sided, ties dropped.",
        "",
        *table(header, rows),
    ]


def _using() -> list[str]:
    return [
        "## Using the bands",
        "",
        "- A mind's run on a seed reads against the bands at the same checkpoints: inside the "
        "`rule:half_full` band is as good as the simple sustained rule; below the `rule:greedy` "
        "band is worse than taking everything in reach.",
        "- Experiment E0 scores minds on the same measures, paired by seed, with these four "
        "baselines run in the same batch (see the E0 pre-registration).",
        "- A test of a baseline's behaviour should take its tolerance from these bands, not from "
        "a single seed.",
    ]


def reference_markdown(data: Mapping[str, Any]) -> str:
    """The page text for ``reference_data`` output plus its ``charts`` list."""
    ref = data["reference"]
    ticks_per_year = ref["ticks_per_year"]
    years = ref["ticks"] // ticks_per_year
    sections = [
        [f"# {ref['world'].upper()} reference bands", "", f"> {ref['purpose']}"],
        _made(ref, ticks_per_year),
        _baselines(data["minds"]),
        _headline(data["minds"], years),
        _by_year(data, ticks_per_year),
        _charts(data),
        _paired(data["paired"]),
        _using(),
    ]
    return "\n\n".join("\n".join(s) for s in sections) + "\n"
