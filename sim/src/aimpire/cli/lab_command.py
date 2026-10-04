"""The ``lab`` subcommand: Tinkering Lab operations (ADR-0020). Arguments in, exit code out.

    aimpire lab twin m0 --set world.gravity=950000 [--set ...] --mind rule:half_full
                        --seeds 1-8 --years 5 [--renderer places|grid] [--out runs/lab]

Exit codes as the other commands: 0 done; 2 a fixable input error (unknown
mind, bad seeds, refused ``--set``, a twin that already exists); 3 refused
over budget, after the worst-case line. Sweeps and forks arrive with LAB2/LAB3.
"""

import argparse
import sys
from pathlib import Path
from typing import Final

from aimpire.cli.commands import BAD_INPUT, OK, OVER_BUDGET, USER_ERRORS
from aimpire.experiments.play import reproduce_command
from aimpire.experiments.preflight import OverBudget
from aimpire.lab.overrides import KnobError, add_set_option
from aimpire.lab.twin import WORLDS, TwinError, TwinOptions, run_twin
from aimpire.rules import DEFAULT_RULES_DIR, RulesError, load_calendar

DEFAULT_MIND: Final = "rule:half_full"
MAX_SEEDS: Final = 10_000


def parse_seeds(text: str) -> tuple[int, ...]:
    """``"1-8"``, ``"3"`` or ``"1,4,6-9"`` into sorted distinct seeds; ``ValueError`` if bad."""
    seeds: set[int] = set()
    for chunk in text.split(","):
        low, sep, high = chunk.strip().partition("-")
        try:
            a = int(low, 10)
            b = int(high, 10) if sep else a
        except ValueError:
            raise ValueError(f"seeds must look like 1-8 or 1,3,5-7, got {text!r}") from None
        if a < 0 or b < a:
            raise ValueError(f"bad seed range {chunk.strip()!r} in {text!r}")
        seeds.update(range(a, b + 1))
        if len(seeds) > MAX_SEEDS:
            raise ValueError(f"at most {MAX_SEEDS} seeds")
    return tuple(sorted(seeds))


def add_lab_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register ``aimpire lab`` and its operations on the top-level subcommands."""
    lab = commands.add_parser("lab", help="Tinkering Lab: twin worlds (ADR-0020)")
    ops = lab.add_subparsers(dest="lab_command", required=True)
    twin = ops.add_parser("twin", help="the baseline and a variant on paired seeds")
    twin.add_argument("world", choices=WORLDS, help="the world to play")
    add_set_option(twin)
    twin.add_argument(
        "--mind",
        default=DEFAULT_MIND,
        help="rule:half_full, rule:greedy, rule:random, rule:msy, mock, or a profile .toml",
    )
    twin.add_argument("--seeds", default="1-8", help="paired seeds, e.g. 1-8 or 1,3,5-7")
    length = twin.add_mutually_exclusive_group()
    length.add_argument("--years", type=int, help="game years per run (default 5)")
    length.add_argument("--ticks", type=int, help="ticks per run, instead of --years")
    twin.add_argument("--renderer", choices=("places", "grid"), default="places")
    twin.add_argument("--out", type=Path, default=Path("runs/lab"), help="runs folder")
    twin.add_argument("--rules", type=Path, default=DEFAULT_RULES_DIR, help="rules version dir")
    twin.add_argument("--council-every", type=int, default=10, help="ticks between councils")
    twin.set_defaults(handler=twin_command)


def _ticks(args: argparse.Namespace) -> int:
    if args.ticks is not None:
        return int(args.ticks)
    years = 5 if args.years is None else int(args.years)
    return years * load_calendar(args.rules).ticks_per_year


def twin_command(args: argparse.Namespace) -> int:
    """``aimpire lab twin``: 0 when both sides of every seed ran and the report is written."""
    argv = args.argv if args.argv is not None else sys.argv[1:]
    if any(n is not None and n < 1 for n in (args.ticks, args.years, args.council_every)):
        print("error: --ticks, --years and --council-every must be at least 1")
        return BAD_INPUT
    try:
        seeds = parse_seeds(args.seeds)
    except ValueError as error:
        print(f"error: {error}")
        return BAD_INPUT
    try:
        opts = TwinOptions(
            world=args.world,
            mind=args.mind,
            seeds=seeds,
            ticks=_ticks(args),
            settings=tuple(args.set),
            renderer=args.renderer,
            out_root=args.out,
            rules_dir=args.rules,
            council_every=args.council_every,
            base_dir=Path.cwd(),
            reproduce=reproduce_command(argv),
        )
        run_twin(opts)
    except OverBudget as refused:
        print(refused)
        return OVER_BUDGET
    except (*USER_ERRORS, KnobError, RulesError, TwinError) as error:
        print(f"error: {error}")
        return BAD_INPUT
    return OK
