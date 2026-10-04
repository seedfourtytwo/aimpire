"""The ``run`` subcommand: play one game (backlog M0c). Arguments in, exit code out.

    aimpire run m0 --mind rule:half_full --seed 1 --years 5 [--set world.gravity=950000]
                   [--renderer places|grid] [--out runs]

Exit codes as the other commands: 0 done; 2 a fixable input error (unknown
mind, bad profile, missing key, refused ``--set``, a run that already
exists); 3 refused over budget, after the worst-case line.
"""

import argparse
import sys
from pathlib import Path
from typing import Final

from aimpire.cli.commands import BAD_INPUT, OK, OVER_BUDGET, USER_ERRORS
from aimpire.experiments.play import WORLDS, PlayOptions, play, reproduce_command
from aimpire.experiments.preflight import OverBudget
from aimpire.lab.overrides import KnobError, add_set_option
from aimpire.rules import DEFAULT_RULES_DIR, RulesError, load_calendar

DEFAULT_MIND: Final = "rule:half_full"


def add_run_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register ``aimpire run`` on the top-level subcommands."""
    run = commands.add_parser("run", help="play one game and write its store, replay, notebook")
    run.add_argument("world", choices=WORLDS, help="the world to play")
    run.add_argument(
        "--mind",
        default=DEFAULT_MIND,
        help="rule:half_full, rule:greedy, rule:random, rule:msy, mock, or a profile .toml",
    )
    run.add_argument("--seed", type=int, default=1, help="world seed")
    length = run.add_mutually_exclusive_group()
    length.add_argument("--years", type=int, help="game years to play (default 5)")
    length.add_argument("--ticks", type=int, help="ticks to play, instead of --years")
    add_set_option(run)
    run.add_argument("--renderer", choices=("places", "grid"), default="places")
    run.add_argument("--out", type=Path, default=Path("runs"), help="runs folder")
    run.add_argument("--rules", type=Path, default=DEFAULT_RULES_DIR, help="rules version dir")
    run.add_argument("--council-every", type=int, default=10, help="ticks between councils")
    run.add_argument("--frame-every", type=int, default=10, help="ticks between replay frames")
    run.set_defaults(handler=run_command)


def _ticks(args: argparse.Namespace) -> int:
    if args.ticks is not None:
        return int(args.ticks)
    years = 5 if args.years is None else int(args.years)
    return years * load_calendar(args.rules).ticks_per_year


def run_command(args: argparse.Namespace) -> int:
    """``aimpire run``: 0 when the game was played and written."""
    argv = args.argv if args.argv is not None else sys.argv[1:]
    counts = (args.ticks, args.years, args.council_every, args.frame_every)
    if any(n is not None and n < 1 for n in counts):
        print("error: --ticks, --years, --council-every and --frame-every must be at least 1")
        return BAD_INPUT
    try:
        opts = PlayOptions(
            world=args.world,
            mind=args.mind,
            seed=args.seed,
            ticks=_ticks(args),
            settings=tuple(args.set),
            renderer=args.renderer,
            out_root=args.out,
            rules_dir=args.rules,
            council_every=args.council_every,
            frame_every=args.frame_every,
            base_dir=Path.cwd(),
            reproduce=reproduce_command(argv),
        )
        play(opts)
    except OverBudget as refused:
        print(refused)
        return OVER_BUDGET
    except (*USER_ERRORS, KnobError, RulesError) as error:
        print(f"error: {error}")
        return BAD_INPUT
    return OK
