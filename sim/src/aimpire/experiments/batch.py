"""``aimpire batch``: run a pre-registered experiment, one run store per run (backlog F6d).

Order of work, so that nothing is spent or written before it is safe:

1. load and validate the experiment file (``experiment``);
2. plan the runs and print the worst case; refuse over budget (``preflight``);
3. refuse if runs of this experiment already exist: with a different file
   hash the file was edited after its runs (``ExperimentChanged``),
   otherwise they would be overwritten;
4. build the providers (a profile's key is read here, before any call);
5. run each planned run in its own ``runs/<run_id>/`` store, whose manifest
   holds the experiment hash (and the pre-registration document's, if the
   file names one), arm, knowledge arm, renderer, rule disclosure, prompt
   hash and seat assignment; the spend of each run counts toward the next
   one's cap. In a world with observer measures, ``measures.json`` beside
   the store holds each seat's measures at every checkpoint;
6. write one report for the experiment (``experiments.report``).

``verify_batch`` re-hashes the file (and its pre-registration document)
later and lists every run recorded under another hash, so a post-hoc edit
of the pre-registration is visible.
"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from aimpire import __version__
from aimpire.cognition.budget import Caps
from aimpire.cognition.minds import build_provider
from aimpire.cognition.protocol import Provider
from aimpire.cognition.runner import run_with_councils
from aimpire.cognition.seats import Seat, seats_for
from aimpire.experiments.experiment import (
    Experiment,
    ExperimentError,
    file_hash,
    load_experiment,
    preregistration_hash,
)
from aimpire.experiments.measures import CheckpointMeasures, has_measures, write_measures
from aimpire.experiments.plan import PlannedRun, cost_plan, plan_runs, run_cap_micro_usd, run_config
from aimpire.experiments.preflight import Echo, check_budget, spent_this_month
from aimpire.experiments.report import write_experiment_report
from aimpire.experiments.summary import RunSummary, summarize
from aimpire.experiments.worlds import World, world_factory
from aimpire.persistence.spend import DB_NAME, current_month
from aimpire.persistence.store import RunStore


class ExperimentChanged(RuntimeError):  # noqa: N818 (names what happened to the file)
    """The experiment file no longer matches the hash its runs recorded."""


@dataclass(frozen=True, slots=True)
class BatchResult:
    """What a batch wrote: the run ids in order and the report files."""

    run_ids: tuple[str, ...]
    report_md: Path
    report_json: Path


def _hashes(file_hash: str, prereg_hash: str) -> str:
    """The file hash, joined with the pre-registration document's when there is one."""
    return f"{file_hash}+{prereg_hash}" if prereg_hash else file_hash


def _recorded(out_root: Path, experiment_id: str) -> list[tuple[str, str]]:
    """``(run_id, hashes)`` of every run of ``experiment_id`` under ``out_root`` (``_hashes``)."""
    found: list[tuple[str, str]] = []
    for db in sorted(out_root.glob(f"*/{DB_NAME}")):
        with RunStore.open(db.parent, read_only=True) as store:
            manifest = store.manifest()
        config: dict[str, Any] = manifest["config"]
        recorded: dict[str, Any] = config.get("experiment", {})
        if recorded.get("id") == experiment_id:
            prereg: dict[str, Any] = config.get("preregistration", {})
            hashes = _hashes(str(recorded.get("file_hash", "")), str(prereg.get("hash", "")))
            found.append((manifest["run_id"], hashes))
    return found


def verify_batch(path: Path, *, out_root: Path) -> list[str]:
    """Run ids under ``out_root`` recorded with a different hash of ``path`` or of its
    pre-registration document; [] if none."""
    try:
        raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ExperimentError(f"{path}: not valid YAML ({exc})") from None
    table: dict[str, Any] = cast(dict[str, Any], raw) if isinstance(raw, dict) else {}
    prereg = table.get("preregistration")
    current = _hashes(file_hash(path), preregistration_hash(path, prereg) if prereg else "")
    return [run_id for run_id, h in _recorded(out_root, str(table.get("id"))) if h != current]


def _refuse_existing(exp: Experiment, out_root: Path) -> None:
    recorded = _recorded(out_root, exp.id)
    current = _hashes(exp.file_hash, exp.preregistration_hash)
    changed = [run_id for run_id, h in recorded if h != current]
    if changed:
        raise ExperimentChanged(
            f"{len(changed)} runs of {exp.id!r} were made from a different version of the "
            f"experiment file or its pre-registration document (first: {changed[0]}); "
            "the pre-registration was edited"
        )
    if recorded:
        raise FileExistsError(f"{exp.id!r} already has runs under {out_root}; use a new folder")


def _create_store(
    exp: Experiment, run: PlannedRun, world: World, *, out_root: Path, month: str
) -> RunStore:
    """The run's own store; its manifest records the design facts and the file hash."""
    return RunStore.create(
        out_root / run.run_id,
        run_id=run.run_id,
        seed=run.seed,
        rules_version=world.state.rules_version,
        rules_hash=world.state.rules_hash,
        caps=Caps(run_micro_usd=run_cap_micro_usd(exp)),
        month=month,
        config=run_config(exp, run, [civ for civ, _ in world.civs]),
        code_version=__version__,
    )


def _drive(  # noqa: PLR0913 (one run's inputs)
    exp: Experiment,
    run: PlannedRun,
    world: World,
    store: RunStore,
    *,
    providers: dict[str, Provider],
    spent_month: int,
) -> None:
    """Advance the world through every council of the run, gated by the budget.

    In a world with observer measures, write each seat's measures beside the store.
    """
    seats = [
        Seat(civ, entity_id, mind, providers[mind.label])
        for (civ, entity_id), mind in zip(world.civs, run.minds, strict=True)
    ]
    build = seats_for(
        seats,
        calendar=world.calendar,
        every_ticks=exp.council_every,
        renderer=run.arm.renderer,
        system=run.arm.prompt_text,
    )
    watch = (
        CheckpointMeasures(exp.world, world, exp.checkpoint_every)
        if has_measures(exp.world)
        else None
    )
    run_loop = run_with_councils(
        world.state,
        world.scheduler,
        ticks=exp.ticks,
        every_ticks=exp.council_every,
        checkpoint_every=exp.checkpoint_every,
        seats_for=build,
        gate=store.budget_guard(spent_month),
        sink=store,
        on_tick=watch,
    )
    asyncio.run(run_loop)
    if watch is not None:
        watch.close(world.state)
        write_measures(watch.data(), store.run_dir)


def _providers(runs: Sequence[PlannedRun]) -> dict[str, Provider]:
    minds = {m.label: m for run in runs for m in run.minds}
    return {label: build_provider(mind) for label, mind in sorted(minds.items())}


def run_batch(
    path: Path, *, out_root: Path, month: str | None = None, echo: Echo = print
) -> BatchResult:
    """Run every planned run of the experiment at ``path``; write the report."""
    exp = load_experiment(path)
    runs = plan_runs(exp)
    month = month or current_month()
    check_budget(cost_plan(exp, runs), runs_root=out_root, month=month, echo=echo)
    _refuse_existing(exp, out_root)
    providers = _providers(runs)
    spent_month = spent_this_month(out_root, month)
    summaries: list[RunSummary] = []
    for run in runs:
        world = world_factory(exp.world)(run.seed, exp.seats)
        with _create_store(exp, run, world, out_root=out_root, month=month) as store:
            _drive(exp, run, world, store, providers=providers, spent_month=spent_month)
            spent_month += store.run_spent()
            summaries.append(summarize(store))
        echo(f"run {run.run_id} done")
    md, js = write_experiment_report(exp, summaries, out_root / exp.id)
    echo(f"report {md}")
    return BatchResult(tuple(r.run_id for r in runs), md, js)
