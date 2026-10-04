"""The runs an experiment file asks for, and what they could cost (ADR-0014 section 1).

Design, in the order runs are listed and executed:

    for arm in arms (file order)
      for seed in seeds                  paired: every arm runs every seed
        for rotation in 0 .. models-1    seat i gets models[(i + rotation) % models]
          for replicate in 0 .. replicates-1

Why cyclic rotation: with ``m`` models, the ``m`` shifts put every model in
every seat exactly as often as the seats allow, so seat effects average out
between models (ADR-0014: every model plays every seat). The world seed is
the run seed: replicates share it, and run-to-run differences come from the
minds alone.

Run ids are built from these indices only, so the same file always gives the
same ids, seeds and, with deterministic minds, the same hashes.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from aimpire.cognition.minds import MindSpec
from aimpire.experiments.experiment import Arm, Experiment
from aimpire.experiments.preflight import CostPlan


@dataclass(frozen=True, slots=True)
class PlannedRun:
    """One run of the design. ``minds`` is the mind in each seat, in seat order."""

    run_id: str
    arm: Arm
    seed: int
    rotation: int
    replicate: int
    minds: tuple[MindSpec, ...]


def rotate(models: Sequence[MindSpec], seats: int, rotation: int) -> tuple[MindSpec, ...]:
    """The mind in each of ``seats`` seats under cyclic ``rotation``."""
    return tuple(models[(seat + rotation) % len(models)] for seat in range(seats))


def plan_runs(exp: Experiment) -> list[PlannedRun]:
    """Every run the experiment asks for, in execution order."""
    runs: list[PlannedRun] = []
    for arm in exp.arms:
        for seed in exp.seeds:
            for rotation in range(len(arm.models)):
                minds = rotate(arm.models, exp.seats, rotation)
                for replicate in range(exp.replicates):
                    run_id = f"{exp.id}-{arm.id}-s{seed}-r{rotation}-k{replicate}"
                    runs.append(PlannedRun(run_id, arm, seed, rotation, replicate, minds))
    return runs


def councils_per_run(exp: Experiment) -> int:
    """Councils held in ``ticks`` days starting at tick 0, one every ``council_every`` days."""
    return -(-exp.ticks // exp.council_every)


def run_cap_micro_usd(exp: Experiment) -> int:
    """The tightest per-run cap of any mind in the experiment."""
    return min(m.run_cap_micro_usd for arm in exp.arms for m in arm.models)


def cost_plan(exp: Experiment, runs: Sequence[PlannedRun]) -> CostPlan:
    """Worst case: councils x seats x each seated mind's worst call, summed over runs."""
    councils = councils_per_run(exp)
    per_run = [councils * sum(m.worst_case_call_micro_usd for m in run.minds) for run in runs]
    return CostPlan(
        total_micro_usd=sum(per_run),
        largest_run_micro_usd=max(per_run, default=0),
        run_cap_micro_usd=run_cap_micro_usd(exp),
    )


def run_config(exp: Experiment, run: PlannedRun, civ_ids: Sequence[str]) -> dict[str, Any]:
    """The manifest ``config`` of a run: the design facts a report or audit needs."""
    return {
        "experiment": {"id": exp.id, "file_hash": exp.file_hash},
        "world": exp.world,
        "arm": run.arm.id,
        "knowledge_arm": run.arm.knowledge_arm,
        "renderer": run.arm.renderer,
        "prompt": {"name": run.arm.prompt, "hash": run.arm.prompt_hash},
        "rotation": run.rotation,
        "replicate": run.replicate,
        "seats": {civ: mind.label for civ, mind in zip(civ_ids, run.minds, strict=True)},
        "ticks": exp.ticks,
        "council_every": exp.council_every,
    }
