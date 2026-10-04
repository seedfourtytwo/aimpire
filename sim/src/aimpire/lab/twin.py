"""``aimpire lab twin``: the baseline and one variant on paired seeds (ADR-0020 section 6, LAB1).

Order of work, so that nothing is spent or written before it is safe:

1. resolve the variant (``--set``; refused values stop here) and the mind
   (no key read);
2. print the worst case of every council of every run on both sides, and
   refuse over budget (``preflight``); rule and mock minds cost nothing;
3. refuse if any run folder or the report folder already exists, so a twin
   is never half overwritten;
4. per seed: run the **baseline** (no overrides at all: an override equal to
   its default would still change the rules hash) and the **variant**, with
   the same mind and seed, recording metrics and part hashes every tick;
5. find each seed's first divergence (``divergence``) and write the report
   (``report.twin``), then print the end-of-run table and the reminder that a
   Lab finding needs a pre-registered re-run (ADR-0014).

Names: the twin id comes from the arguments only (world, mind, seeds, length,
renderer, cadence, variant id), so the same arguments name the same twin.
Runs are ``<twin_id>-s<seed>-<side>`` directly under the runs folder; the
report is ``<out>/<twin_id>/``.
"""

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from aimpire.cognition.minds import MindSpec, resolve_mind
from aimpire.cognition.seats import RENDERERS, Renderer
from aimpire.experiments.preflight import CostPlan, Echo, check_budget, spent_this_month, usd
from aimpire.lab.divergence import Divergence, first_divergence
from aimpire.lab.knobs import Layer
from aimpire.lab.physics_view import physics_rows
from aimpire.lab.twin_side import BASELINE, TWIN_METRICS, VARIANT, SideRun, SideSpec, run_side
from aimpire.lab.variant import EXPLORATORY, ResolvedVariant, resolve_variant
from aimpire.persistence.spend import current_month
from aimpire.report.twin import REMINDER, MetricSeries, end_summary, summary_line, write_twin_report
from aimpire.rules import load_calendar

WORLDS: Final = ("m0",)


class TwinError(ValueError):
    """Twin arguments a user can fix: an unknown world, no or repeated seeds, a zero length."""


@dataclass(frozen=True, slots=True)
class TwinOptions:
    """Everything that defines a twin. ``reproduce`` is the command line that gives it."""

    world: str
    mind: str
    seeds: tuple[int, ...]
    ticks: int
    settings: tuple[str, ...]
    renderer: Renderer
    out_root: Path
    rules_dir: Path
    council_every: int
    base_dir: Path
    reproduce: str


@dataclass(frozen=True, slots=True)
class TwinResult:
    """The report, each seed's divergence, and the printed lines."""

    twin_id: str
    report: Path
    divergences: tuple[Divergence, ...]
    lines: tuple[str, ...]


def seeds_label(seeds: Sequence[int]) -> str:
    """``s1-8`` for a run of consecutive seeds, else ``s`` plus a short hash of the list."""
    if list(seeds) == list(range(seeds[0], seeds[0] + len(seeds))):
        return f"s{seeds[0]}-{seeds[-1]}"
    digest = hashlib.blake2b(",".join(map(str, seeds)).encode(), digest_size=4).hexdigest()
    return f"s{digest}"


def twin_id_for(opts: TwinOptions, mind: MindSpec, resolved: ResolvedVariant) -> str:
    """``twin-<world>-<mind>-<seeds>-t<ticks>-<renderer>-c<cadence>-v<variant>``."""
    label = re.sub(r"[^a-z0-9]+", "-", mind.label.lower()).strip("-")
    return (
        f"twin-{opts.world}-{label}-{seeds_label(opts.seeds)}-t{opts.ticks}-{opts.renderer}"
        f"-c{opts.council_every}-v{resolved.variant.variant_id[:8]}"
    )


def _specs(opts: TwinOptions, twin_id: str, resolved: dict[str, ResolvedVariant]) -> list[SideSpec]:
    """Both sides of every seed, baseline first. The variant honours ``mind.renderer``."""
    variant_renderer = resolved[VARIANT].variant.layer_values(Layer.MIND).get("renderer")
    specs: list[SideSpec] = []
    for seed in opts.seeds:
        for side in (BASELINE, VARIANT):
            r = resolved[side]
            renderer: Renderer = opts.renderer
            if side == VARIANT and variant_renderer in RENDERERS:
                renderer = "grid" if variant_renderer == "grid" else "places"
            config = {
                "command": "lab twin",
                "world": opts.world,
                "renderer": renderer,
                "ticks": opts.ticks,
                "council_every": opts.council_every,
                "twin": {"id": twin_id, "side": side, "seed": seed},
                **r.manifest_config(),
                "tags": sorted({EXPLORATORY, *r.tags}),
            }
            settings = opts.settings if side == VARIANT else ()
            specs.append(
                SideSpec(side, seed, f"{twin_id}-s{seed}-{side}", settings, renderer, config)
            )
    return specs


def _refuse_existing(out_root: Path, report_dir: Path, specs: Sequence[SideSpec]) -> None:
    for path in (report_dir, *(out_root / s.run_id for s in specs)):
        if path.exists():
            raise FileExistsError(f"{path} already exists; a twin is never overwritten")


def _check(opts: TwinOptions) -> None:
    if opts.world not in WORLDS:
        raise TwinError(f"unknown world {opts.world!r}; aimpire lab twin plays {list(WORLDS)}")
    if not opts.seeds or len(set(opts.seeds)) != len(opts.seeds):
        raise TwinError("a twin needs one or more distinct seeds")
    if opts.ticks < 1 or opts.council_every < 1:
        raise TwinError("ticks and council cadence must be at least 1")


def run_twin(opts: TwinOptions, *, month: str | None = None, echo: Echo = print) -> TwinResult:
    """Run the twin described by ``opts`` (module docstring for the order of work)."""
    _check(opts)
    resolved = {
        BASELINE: resolve_variant(opts.rules_dir, ()),
        VARIANT: resolve_variant(opts.rules_dir, opts.settings),
    }
    mind = resolve_mind(opts.mind, opts.base_dir)
    month = month or current_month()
    per_run = -(-opts.ticks // opts.council_every) * mind.worst_case_call_micro_usd
    total = 2 * len(opts.seeds) * per_run
    check_budget(
        CostPlan(total, per_run, mind.run_cap_micro_usd),
        runs_root=opts.out_root,
        month=month,
        echo=echo,
    )
    twin_id = twin_id_for(opts, mind, resolved[VARIANT])
    report_dir = opts.out_root / twin_id
    specs = _specs(opts, twin_id, resolved)
    _refuse_existing(opts.out_root, report_dir, specs)
    echo(f"twin {twin_id}: {len(specs)} runs, tags {', '.join(specs[-1].config['tags'])}")
    spent_month = spent_this_month(opts.out_root, month)
    runs: list[SideRun] = []
    for spec in specs:
        run = run_side(
            spec,
            mind=mind,
            rules_dir=opts.rules_dir,
            ticks=opts.ticks,
            council_every=opts.council_every,
            out_root=opts.out_root,
            month=month,
            spent_month=spent_month,
        )
        spent_month += run.charged_micro_usd
        runs.append(run)
        echo(f"run {spec.run_id} done: final hash {run.final_hash[:16]}")
    return _report(
        opts, runs, mind_label=mind.label, report_dir=report_dir, resolved=resolved, echo=echo
    )


def _report(  # noqa: PLR0913 (the finished twin's parts)
    opts: TwinOptions,
    runs: Sequence[SideRun],
    *,
    mind_label: str,
    report_dir: Path,
    resolved: dict[str, ResolvedVariant],
    echo: Echo,
) -> TwinResult:
    pairs = [(runs[i], runs[i + 1]) for i in range(0, len(runs), 2)]
    ticks = pairs[0][0].metrics.ticks()
    divergences = tuple(first_divergence(b.spec.seed, ticks, b.hashes, v.hashes) for b, v in pairs)
    metrics = [
        MetricSeries(
            name,
            opts.seeds,
            tuple(tuple(b.metrics.series(name)) for b, _ in pairs),
            tuple(tuple(v.metrics.series(name)) for _, v in pairs),
        )
        for name in TWIN_METRICS
    ]
    end = [end_summary(m) for m in metrics]
    data: dict[str, Any] = {
        "twin_id": report_dir.name,
        "world": opts.world,
        "mind": mind_label,
        "renderer": opts.renderer,
        "seeds": list(opts.seeds),
        "ticks": opts.ticks,
        "ticks_per_year": load_calendar(opts.rules_dir).ticks_per_year,
        "council_every": opts.council_every,
        "variant": resolved[VARIANT].variant.manifest_entry(),
        "tags": list(runs[-1].spec.config["tags"]),
        "rules_hash": {side: resolved[side].rules_hash for side in (BASELINE, VARIANT)},
        "physics": physics_rows(resolved[VARIANT].derived),
        "divergence": [d.to_json() for d in divergences],
        "end": end,
        "runs": [
            {
                "seed": r.spec.seed,
                "side": r.spec.side,
                "run_id": r.spec.run_id,
                "final_hash": r.final_hash,
                "charged_micro_usd": r.charged_micro_usd,
            }
            for r in runs
        ],
        "reproduce": opts.reproduce,
    }
    path = write_twin_report(data, ticks, metrics, report_dir)
    lines = _summary(divergences, end, sum(r.charged_micro_usd for r in runs), path)
    for line in lines:
        echo(line)
    return TwinResult(report_dir.name, path, divergences, tuple(lines))


def _summary(
    divergences: Sequence[Divergence], end: Sequence[dict[str, Any]], charged: int, path: Path
) -> list[str]:
    lines = ["seed  first divergence"]
    for d in divergences:
        where = (
            "never" if d.first_tick is None else f"tick {d.first_tick}: {', '.join(d.first_parts)}"
        )
        lines.append(f"{d.seed:>4}  {where}")
    lines.append(
        f"{'metric at the end':<28} {'baseline':>9} {'variant':>9}  variant - baseline [10 %, 90 %]"
    )
    for row in end:
        lines.append(
            f"{row['metric']:<28} {row['baseline_median']:>9} {row['variant_median']:>9}  "
            + summary_line(row)
        )
    lines += [
        "stores and near camp in food units; harvest in mu per forager-tick, trailing season",
        f"cost charged {usd(charged)}",
        f"wrote {path}",
        REMINDER,
    ]
    return lines
