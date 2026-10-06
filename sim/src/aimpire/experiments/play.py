"""``aimpire run``: play one M0 game with one mind and write everything it needs (backlog M0c).

Order of work, so that nothing is spent or written before it is safe:

1. resolve the Lab variant (``--set``) and build the world from the rules
   directory with it, so the overrides reach the physics (``build_m0_run``);
2. resolve the mind by name (no key read) and print the worst-case cost of
   every council; refuse over budget (``preflight``);
3. build the provider (a profile's key is read here, before any call). A
   rule baseline gets the disclosed rule of the same rules directory;
4. create ``<out>/<run_id>/`` with its run store; the run id comes from the
   arguments only, so the same arguments name the same run (and refuse to
   overwrite it);
5. run every tick with councils on cadence through the budget gate,
   recording metrics each tick and a replay frame every ``frame_every``;
6. write ``metrics.csv``, ``replay.json`` (format ``aimpire-replay-v2``, with
   each council's decision taken from the run store; open it in
   ``client/replay/``) and ``notebook.md``, and print the summary.

Same arguments, same hashes: every checkpoint hash, the replay and the
notebook are byte-identical between two runs into different folders.
"""

import asyncio
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from aimpire import __version__
from aimpire.cognition.baselines import rule_provider
from aimpire.cognition.budget import Caps
from aimpire.cognition.disclosed import load_disclosed
from aimpire.cognition.minds import MindSpec, build_provider, resolve_mind
from aimpire.cognition.protocol import Provider
from aimpire.cognition.reachability import check_reachable
from aimpire.cognition.render import system_prompt
from aimpire.cognition.runner import run_with_councils
from aimpire.cognition.seats import Renderer, Seat, seats_for
from aimpire.experiments.m0_world import build_m0_run
from aimpire.experiments.preflight import CostPlan, Echo, check_budget, spent_this_month, usd
from aimpire.experiments.progress import ProgressSink
from aimpire.experiments.worlds import World
from aimpire.lab.variant import ResolvedVariant, resolve_variant
from aimpire.persistence.spend import current_month
from aimpire.persistence.store import RunStore
from aimpire.report.m0_run import CIV_KIND, camp_dot, m0_measures, summary_lines
from aimpire.report.metrics import MetricsRecorder
from aimpire.report.notebook import RunInfo, write_notebook
from aimpire.report.replay import write_replay_doc
from aimpire.report.replay_m0 import M0ReplayRecorder, councils_section, run_section
from aimpire.sim.presets import PRESETS
from aimpire.sim.state import WorldState
from aimpire.sim.systems.tribe import population
from aimpire.sim.world.m0 import FOOD

WORLDS: Final = ("m0",)
"""The worlds ``aimpire run`` can play; experiments name others through ``batch``."""


@dataclass(frozen=True, slots=True)
class PlayOptions:
    """Everything that defines a run. ``reproduce`` is the command line that gives it."""

    world: str
    mind: str
    seed: int
    ticks: int
    settings: tuple[str, ...]
    renderer: Renderer
    out_root: Path
    rules_dir: Path
    council_every: int
    frame_every: int
    base_dir: Path
    reproduce: str


@dataclass(frozen=True, slots=True)
class PlayResult:
    """Where the run went and its final state hash."""

    run_id: str
    run_dir: Path
    final_hash: str
    lines: tuple[str, ...]


def run_id_for(opts: PlayOptions, mind: MindSpec, resolved: ResolvedVariant) -> str:
    """``<world>-<mind>-s<seed>-t<ticks>-<renderer>-c<cadence>-<variant>`` from the arguments."""
    label = re.sub(r"[^a-z0-9]+", "-", mind.label.lower()).strip("-")
    return (
        f"{opts.world}-{label}-s{opts.seed}-t{opts.ticks}-{opts.renderer}"
        f"-c{opts.council_every}-v{resolved.variant.variant_id[:8]}"
    )


def _provider(mind: MindSpec, rules_dir: Path) -> Provider:
    if mind.kind == "rule":
        return rule_provider(mind.rule, load_disclosed(rules_dir))
    return build_provider(mind)


def _config(opts: PlayOptions, mind: MindSpec, resolved: ResolvedVariant) -> dict[str, Any]:
    return {
        "command": "run",
        "world": opts.world,
        "seats": {"C1": mind.label},
        "renderer": opts.renderer,
        "ticks": opts.ticks,
        "council_every": opts.council_every,
        **resolved.manifest_config(),
    }


class _Watch:
    """The runner's per-tick hook: metrics every tick, a replay frame every ``frame_every``."""

    def __init__(self, world: World, opts: PlayOptions, start_people: int) -> None:
        self.frame_every = opts.frame_every
        self.metrics = MetricsRecorder(m0_measures(world.civs[0][1], start_people))
        self.replay = M0ReplayRecorder(FOOD, [CIV_KIND], world.calendar, locate=camp_dot)
        self.metrics.record(world.state)
        self.replay.capture(world.state)

    def __call__(self, state: WorldState) -> None:
        self.metrics.record(state)
        if state.tick % self.frame_every == 0:
            self.replay.capture(state)

    def close(self, state: WorldState) -> None:
        if self.replay.last_tick != state.tick:
            self.replay.capture(state)


def play(
    opts: PlayOptions,
    *,
    month: str | None = None,
    echo: Echo = print,
    provider: Provider | None = None,
) -> PlayResult:
    """Run one game as described by ``opts`` (module docstring for the order of work).

    ``provider`` replaces the one the mind names; for offline test doubles only
    (the fixture replay's scripted mind), never to change a mind's price.
    """
    if opts.world not in WORLDS:
        raise ValueError(f"unknown world {opts.world!r}; aimpire run plays {list(WORLDS)}")
    if opts.ticks < 1 or opts.council_every < 1 or opts.frame_every < 1:
        raise ValueError("ticks, council cadence and frame interval must be at least 1")
    resolved = resolve_variant(opts.rules_dir, opts.settings)
    world = build_m0_run(opts.seed, opts.rules_dir, settings=opts.settings)
    mind = resolve_mind(opts.mind, opts.base_dir)
    month = month or current_month()
    councils = -(-opts.ticks // opts.council_every)
    worst = councils * mind.worst_case_call_micro_usd
    check_budget(
        CostPlan(worst, worst, mind.run_cap_micro_usd),
        runs_root=opts.out_root,
        month=month,
        echo=echo,
    )
    if provider is None:
        check_reachable(mind)  # a dead local server stops here, not after a whole run
    provider = provider or _provider(mind, opts.rules_dir)
    run_id = run_id_for(opts, mind, resolved)
    if resolved.tags:
        echo(f"tags: {', '.join(resolved.tags)}")
    spent_month = spent_this_month(opts.out_root, month)
    with RunStore.create(
        opts.out_root / run_id,
        run_id=run_id,
        seed=opts.seed,
        rules_version=world.state.rules_version,
        rules_hash=world.state.rules_hash,
        caps=Caps(run_micro_usd=mind.run_cap_micro_usd),
        month=month,
        config=_config(opts, mind, resolved),
        code_version=__version__,
    ) as store:
        watch = _Watch(world, opts, population(world.state.entities[world.civs[0][1]]))
        _drive(
            world,
            opts,
            seat=Seat("C1", world.civs[0][1], mind, provider),
            store=store,
            watch=watch,
            spent_month=spent_month,
            echo=echo if mind.kind == "profile" else None,
        )
        decisions = store.decisions()
        outcomes = Counter(str(row["outcome"]) for row in decisions)
        charged, final_hash = store.run_spent(), store.checkpoints()[-1][2]
        replay = watch.replay.to_dict(
            watch.metrics,
            councils_section(decisions, store.blobs.get),
            run_section(store.manifest()),
        )
    run_dir = opts.out_root / run_id
    write_replay_doc(replay, run_dir / "replay.json")
    _write_outputs(run_dir, opts, world, watch, outcomes)
    footer = (
        f"cost charged {usd(charged)} (worst case {usd(worst)})",
        f"run {run_id}: final hash {final_hash[:16]}",
        f"wrote {run_dir}: run.db, replay.json, notebook.md, metrics.csv",
    )
    lines = summary_lines(watch.metrics, world.calendar.ticks_per_year, outcomes, footer)
    for line in lines:
        echo(line)
    return PlayResult(run_id, run_dir, final_hash, tuple(lines))


def _drive(  # noqa: PLR0913 (one run's parts)
    world: World,
    opts: PlayOptions,
    *,
    seat: Seat,
    store: RunStore,
    watch: _Watch,
    spent_month: int,
    echo: Echo | None = None,
) -> None:
    """Play every tick; with ``echo`` (live minds only), print a line per council."""
    councils = -(-opts.ticks // opts.council_every)
    sink = store if echo is None else ProgressSink(store, councils=councils, echo=echo)
    build = seats_for(
        [seat],
        calendar=world.calendar,
        every_ticks=opts.council_every,
        renderer=opts.renderer,
        system=system_prompt(),
        walk_speed=world.walk_speed,
    )
    asyncio.run(
        run_with_councils(
            world.state,
            world.scheduler,
            ticks=opts.ticks,
            every_ticks=opts.council_every,
            checkpoint_every=world.calendar.ticks_per_season,
            seats_for=build,
            gate=store.budget_guard(spent_month),
            sink=sink,
            on_tick=watch,
        )
    )
    watch.close(world.state)


def _write_outputs(
    run_dir: Path, opts: PlayOptions, world: World, watch: _Watch, outcomes: Counter[str]
) -> None:
    watch.metrics.write_csv(run_dir / "metrics.csv")
    info = RunInfo(
        run_id=run_dir.name,
        seed=opts.seed,
        rules_version=world.state.rules_version,
        rules_hash=world.state.rules_hash,
        preset=PRESETS["m0"],
        ticks=opts.ticks,
        reproduce=opts.reproduce,
    )
    write_notebook(
        run_dir / "notebook.md", info, watch.metrics, world.scheduler.ledger, dict(outcomes)
    )


def reproduce_command(argv: Sequence[str]) -> str:
    """The command line as given, minus ``--out`` (a folder of the caller's choice)."""
    words: list[str] = []
    skip = False
    for word in argv:
        if skip:
            skip = False
            continue
        if word == "--out":
            skip = True
            continue
        if not word.startswith("--out="):
            words.append(word)
    return " ".join(["aimpire", *words])
