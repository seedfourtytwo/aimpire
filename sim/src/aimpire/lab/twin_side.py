"""One side of a twin: a full M0 run that also records metrics and part hashes every tick (LAB1).

Why not ``aimpire run``: a twin needs, besides the run store, the state's
part hashes after every tick (for the first divergence) and the twin's own
metrics, and it does not need a replay or a notebook per side. The run itself
is the same: the world comes from ``build_m0_run`` with the side's settings,
councils go through the same seat builder, budget gate and run store, so a
twin side replays like any run.

Each side's store lives directly under the runs folder (``<out>/<run_id>/``),
so the monthly spend count (``persistence.spend``) sees it. Its manifest
records the twin (id, side, seed) and the tags, ``exploratory`` always:
every Lab run is exploratory (ADR-0020 section 6).
"""

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from aimpire import __version__
from aimpire.cognition.baselines import rule_provider
from aimpire.cognition.budget import Caps
from aimpire.cognition.disclosed import load_disclosed
from aimpire.cognition.minds import MindSpec, build_provider
from aimpire.cognition.protocol import Provider
from aimpire.cognition.render import system_prompt
from aimpire.cognition.runner import run_with_councils
from aimpire.cognition.seats import Renderer, Seat, seats_for
from aimpire.experiments.m0_world import build_m0_run
from aimpire.experiments.worlds import World
from aimpire.persistence.store import RunStore
from aimpire.report.harvest_rate import HarvestRate
from aimpire.report.m0_run import m0_measures
from aimpire.report.metrics import MetricFn, MetricsRecorder
from aimpire.sim.hashing import subsystem_hashes
from aimpire.sim.state import WorldState
from aimpire.sim.systems.tribe import population

BASELINE: Final = "baseline"
VARIANT: Final = "variant"
SIDES: Final = (BASELINE, VARIANT)

TWIN_METRICS: Final = (
    "population",
    "stores_mu",
    "near_camp_mu",
    "deaths",
    "harvest_per_forager_tick_mu",
)
"""The metrics every twin records, in report order (units: ``report.m0_run``, ``harvest_rate``)."""


@dataclass(frozen=True, slots=True)
class SideSpec:
    """What makes one side: its seed, its ``--set`` settings, renderer and manifest config."""

    side: str
    seed: int
    run_id: str
    settings: tuple[str, ...]
    renderer: Renderer
    config: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class SideRun:
    """What a twin report needs from one finished side."""

    spec: SideSpec
    metrics: MetricsRecorder
    hashes: tuple[dict[str, str], ...]
    """``subsystem_hashes`` at every recorded tick, aligned with ``metrics.ticks()``."""
    final_hash: str
    charged_micro_usd: int


def twin_measures(world: World, window: int) -> dict[str, MetricFn]:
    """The ``TWIN_METRICS`` of the world's first tribe; ``window`` ticks for the harvest rate."""
    entity_id = world.civs[0][1]
    start = population(world.state.entities[entity_id])
    m0 = m0_measures(entity_id, start)
    rate = HarvestRate(world.scheduler.ledger, entity_id, window)
    measures = {name: m0[name] for name in TWIN_METRICS if name in m0}
    measures["harvest_per_forager_tick_mu"] = rate
    return {name: measures[name] for name in TWIN_METRICS}


def side_provider(mind: MindSpec, rules_dir: Path) -> Provider:
    """A fresh provider; a rule baseline plays under the disclosed rule of ``rules_dir``."""
    if mind.kind == "rule":
        return rule_provider(mind.rule, load_disclosed(rules_dir))
    return build_provider(mind)


class _Watch:
    """Per-tick hook: metrics and part hashes. Reads the state, never changes it."""

    def __init__(self, world: World, window: int) -> None:
        self.metrics = MetricsRecorder(twin_measures(world, window))
        self.hashes: list[dict[str, str]] = []
        self(world.state)

    def __call__(self, state: WorldState) -> None:
        self.metrics.record(state)
        self.hashes.append(subsystem_hashes(state))


def run_side(  # noqa: PLR0913 (one run's parts)
    spec: SideSpec,
    *,
    mind: MindSpec,
    rules_dir: Path,
    ticks: int,
    council_every: int,
    out_root: Path,
    month: str,
    spent_month: int,
) -> SideRun:
    """Play one side to the end; write its run store and ``metrics.csv``."""
    world = build_m0_run(spec.seed, rules_dir, settings=spec.settings)
    seat = Seat(world.civs[0][0], world.civs[0][1], mind, side_provider(mind, rules_dir))
    watch = _Watch(world, world.calendar.ticks_per_season)
    run_dir = out_root / spec.run_id
    with RunStore.create(
        run_dir,
        run_id=spec.run_id,
        seed=spec.seed,
        rules_version=world.state.rules_version,
        rules_hash=world.state.rules_hash,
        caps=Caps(run_micro_usd=mind.run_cap_micro_usd),
        month=month,
        config=spec.config,
        code_version=__version__,
    ) as store:
        build = seats_for(
            [seat],
            calendar=world.calendar,
            every_ticks=council_every,
            renderer=spec.renderer,
            system=system_prompt(),
            walk_speed=world.walk_speed,
        )
        asyncio.run(
            run_with_councils(
                world.state,
                world.scheduler,
                ticks=ticks,
                every_ticks=council_every,
                checkpoint_every=world.calendar.ticks_per_season,
                seats_for=build,
                gate=store.budget_guard(spent_month),
                sink=store,
                on_tick=watch,
            )
        )
        final_hash, charged = store.checkpoints()[-1][2], store.run_spent()
    watch.metrics.write_csv(run_dir / "metrics.csv")
    return SideRun(spec, watch.metrics, tuple(watch.hashes), final_hash, charged)
