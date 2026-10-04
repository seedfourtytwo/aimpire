"""Command-line entry point for ``aimpire`` and its short alias ``aim``.

Subcommands:
    qualify <profile.toml | mock | rule[:name]>   frozen observations through one mind
    batch <experiment.yaml> [--verify]            a pre-registered experiment
    run m0 --mind <mind> --seed N --years Y       one game: run store, replay, notebook
    lab twin m0 --set k=v --seeds 1-8 --years Y   baseline and variant on paired seeds

Exit codes: 0 done (qualify passed, verify clean); 1 qualify failed its marks
or verify found an edited experiment file; 2 bad arguments or input files;
3 refused over budget (nothing was called).

Further subcommands (replay, lab sweep, ...) arrive with their epics.
"""

import argparse
from collections.abc import Sequence
from pathlib import Path

from aimpire import __version__
from aimpire.cli.commands import batch_command, qualify_command
from aimpire.cli.lab_command import add_lab_parser
from aimpire.cli.run_command import add_run_parser


def build_parser() -> argparse.ArgumentParser:
    """Return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="aimpire",
        description="Deterministic civilization research simulator.",
    )
    parser.add_argument("--version", action="version", version=f"aimpire {__version__}")
    commands = parser.add_subparsers(dest="command")

    qualify = commands.add_parser("qualify", help="put one mind through the frozen observations")
    qualify.add_argument("mind", help="a profile .toml path, mock, rule or rule:<name>")
    qualify.add_argument("--runs", type=Path, default=Path("runs"), help="runs folder")
    qualify.add_argument("--cases", type=Path, help="cases file (default: the built-in set)")
    qualify.add_argument("--thresholds", type=Path, help="thresholds file (default: built-in)")
    qualify.set_defaults(handler=qualify_command)

    batch = commands.add_parser("batch", help="run a pre-registered experiment file")
    batch.add_argument("experiment", type=Path, help="experiment .yaml file")
    batch.add_argument("--out", type=Path, default=Path("runs"), help="runs folder")
    batch.add_argument(
        "--verify", action="store_true", help="only check the file against its recorded runs"
    )
    batch.set_defaults(handler=batch_command)

    add_run_parser(commands)
    add_lab_parser(commands)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments and run. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    args.argv = None if argv is None else list(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
