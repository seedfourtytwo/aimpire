"""Reference ensembles: rule baselines over many seeds, giving the bands a mind is read against.

ADR-0014 section 1: tolerance bands for rule-baseline tests come from a
reference ensemble of several hundred seeds, and baseline scores are
published beside model scores. Backlog M0d makes the first one,
``experiments/m0-reference.yaml`` (its format: ``reference_file``).

Why not an ordinary experiment file: an experiment needs at least three
replicates per seed (ADR-0014), because a model may answer differently each
time. A rule baseline cannot: the same seed gives the same run, byte for
byte (``test_run_cli_is_reproducible``), so replicates would repeat the same
numbers. A reference therefore accepts rule minds only, runs each seed once,
and keeps no run store: it records the observer measures (``measures``) and
each run's final state hash, which is enough to reproduce and audit it.

Runs go through the same path a mind's run does: the world factory, the
seat builder, the council runner and the validator. ``jobs`` spreads the
independent runs over processes; results are sorted, so the output does not
depend on the number of jobs.
"""

import asyncio
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Any, Final

from aimpire.cognition.budget import BudgetGuard, Caps
from aimpire.cognition.council import Settled
from aimpire.cognition.minds import MindSpec, build_provider
from aimpire.cognition.render import system_prompt
from aimpire.cognition.runner import run_with_councils
from aimpire.cognition.seats import Seat, seats_for
from aimpire.experiments.measures import MEASURE_NAMES, CheckpointMeasures
from aimpire.experiments.reference_file import KIND, ReferenceSpec, is_reference, load_reference
from aimpire.experiments.stats import describe, paired, quantile
from aimpire.experiments.worlds import world_factory
from aimpire.sim.hashing import state_hash
from aimpire.sim.state import WorldState

__all__ = [
    "KIND",
    "ReferenceResult",
    "ReferenceRun",
    "ReferenceSpec",
    "is_reference",
    "load_reference",
    "reference_data",
    "run_reference",
]

RENDERER: Final = "places"  # rule minds read the typed observation; the text is unused


@dataclass(frozen=True, slots=True)
class ReferenceRun:
    """One baseline on one seed: its measures (one seat) and its final state hash."""

    mind: str
    seed: int
    checkpoints: tuple[int, ...]
    measures: dict[str, list[int]]
    final_hash: str
    rules: tuple[str, str, int]
    """``(rules_version, rules_hash, ticks_per_year)`` of the world it ran in."""


@dataclass(frozen=True, slots=True)
class ReferenceResult:
    """Every run of a reference, sorted by mind (file order) and seed, and what was run."""

    seeds: tuple[int, ...]
    ticks: int
    runs: tuple[ReferenceRun, ...]


class _Discard:
    """A council sink that keeps nothing: a reference keeps measures and the final hash."""

    def record_council(self, tick: int, council: int, settled: Sequence[Settled]) -> None:
        pass

    def checkpoint(self, state: WorldState, label: str) -> None:
        pass


def run_one(spec: ReferenceSpec, mind: MindSpec, seed: int, ticks: int) -> ReferenceRun:
    """Play ``mind`` on world ``seed`` for ``ticks`` ticks and measure it."""
    world = world_factory(spec.world)(seed, 1)
    seats = [Seat(civ, eid, mind, build_provider(mind)) for civ, eid in world.civs]
    build = seats_for(
        seats,
        calendar=world.calendar,
        every_ticks=spec.council_every,
        renderer=RENDERER,
        system=system_prompt(),
    )
    watch = CheckpointMeasures(spec.world, world, spec.checkpoint_every)
    asyncio.run(
        run_with_councils(
            world.state,
            world.scheduler,
            ticks=ticks,
            every_ticks=spec.council_every,
            checkpoint_every=spec.checkpoint_every,
            seats_for=build,
            gate=BudgetGuard(Caps()),
            sink=_Discard(),
            on_tick=watch,
        )
    )
    watch.close(world.state)
    (civ, _), *_ = world.civs
    data = watch.data()
    return ReferenceRun(
        mind=mind.label,
        seed=seed,
        checkpoints=tuple(data["checkpoints"]),
        measures=data["civs"][civ],
        final_hash=state_hash(world.state),
        rules=(world.state.rules_version, world.state.rules_hash, world.calendar.ticks_per_year),
    )


def _run_task(task: tuple[ReferenceSpec, MindSpec, int, int]) -> ReferenceRun:
    """Process-pool entry point: a module-level function, so it pickles. Importing this
    module imports ``aimpire.experiments`` first, which registers the worlds in a new process."""
    return run_one(*task)


def run_reference(
    spec: ReferenceSpec,
    *,
    seeds: Sequence[int] | None = None,
    ticks: int | None = None,
    jobs: int = 1,
) -> ReferenceResult:
    """Run every mind on every seed (or a subset, or fewer ticks, for tests)."""
    seeds = tuple(spec.seeds if seeds is None else seeds)
    ticks = spec.ticks if ticks is None else ticks
    tasks = [(spec, mind, seed, ticks) for mind in spec.minds for seed in seeds]
    if jobs > 1:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            runs = list(pool.map(_run_task, tasks, chunksize=4))
    else:
        runs = [run_one(*task) for task in tasks]
    return ReferenceResult(seeds, ticks, tuple(runs))


def _bands(runs: Sequence[ReferenceRun], checkpoints: int) -> dict[str, dict[str, list[int]]]:
    """Per measure, the 10th percentile, lower median and 90th percentile at each checkpoint."""
    bands: dict[str, dict[str, list[int]]] = {}
    for name in MEASURE_NAMES:
        columns = [[r.measures[name][i] for r in runs] for i in range(checkpoints)]
        bands[name] = {
            "q10": [quantile(c, 100) for c in columns],
            "median": [quantile(c, 500) for c in columns],
            "q90": [quantile(c, 900) for c in columns],
        }
    return bands


def _survival(runs: Sequence[ReferenceRun]) -> dict[str, int]:
    """Seeds where at least 90 % of the starting people are alive at the end."""
    kept = sum(10 * r.measures["population"][-1] >= 9 * r.measures["population"][0] for r in runs)
    return {"seeds": len(runs), "kept_90pct": kept}


def reference_data(spec: ReferenceSpec, result: ReferenceResult) -> dict[str, Any]:
    """The whole reference as plain JSON-ready data (integers and sorted lists only)."""
    checkpoints = list(result.runs[0].checkpoints) if result.runs else []
    by_mind = {m.label: [r for r in result.runs if r.mind == m.label] for m in spec.minds}
    finals = {
        mind: {r.seed: r.measures["population"][-1] for r in runs} for mind, runs in by_mind.items()
    }
    labels = [m.label for m in spec.minds]
    rules = sorted({r.rules for r in result.runs})
    if len(rules) > 1:
        raise ValueError(f"runs of one reference used different rules: {rules}")
    return {
        "reference": {
            "id": spec.id,
            "file_hash": spec.file_hash,
            "purpose": spec.purpose,
            "world": spec.world,
            "ticks": result.ticks,
            "council_every": spec.council_every,
            "checkpoint_every": spec.checkpoint_every,
            "seeds": list(result.seeds),
            "renderer": RENDERER,
            "rules_version": rules[0][0] if rules else "",
            "rules_hash": rules[0][1] if rules else "",
            "ticks_per_year": rules[0][2] if rules else 0,
        },
        "checkpoints": checkpoints,
        "measures": list(MEASURE_NAMES),
        "minds": [
            {
                "mind": mind,
                "bands": _bands(runs, len(checkpoints)),
                "final": {n: describe([r.measures[n][-1] for r in runs]) for n in MEASURE_NAMES},
                "survival": _survival(runs),
            }
            for mind, runs in by_mind.items()
        ],
        "paired": [
            {"a": a, "b": b, "metric": "final_population", **paired(finals[a], finals[b])}
            for i, a in enumerate(labels)
            for b in labels[i + 1 :]
        ],
        "runs": [
            {
                "mind": r.mind,
                "seed": r.seed,
                "final_hash": r.final_hash,
                "final": {n: r.measures[n][-1] for n in MEASURE_NAMES},
            }
            for r in result.runs
        ],
    }
