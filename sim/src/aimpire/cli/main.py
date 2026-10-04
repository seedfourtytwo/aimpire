"""Command-line entry point for ``aimpire`` and its short alias ``aim``.

Subcommands (run, replay, batch, qualify, ...) arrive with their epics.
"""

import argparse
from collections.abc import Sequence

from aimpire import __version__


def build_parser() -> argparse.ArgumentParser:
    """Return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="aimpire",
        description="Deterministic civilization research simulator.",
    )
    parser.add_argument("--version", action="version", version=f"aimpire {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments and run. Returns a process exit code."""
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
