"""Generate the mind contract's JSON schemas into ``schema/``.

Usage (from ``sim/``; the ``just`` recipes wrap these):

    uv run python -m aimpire.contracts.export ../schema           # write
    uv run python -m aimpire.contracts.export --check ../schema   # fail on drift

Why canonical text: the files are committed and diffed in CI, so the bytes must
not depend on dict order. Keys are sorted, indent is two spaces, and each file
ends in exactly one newline.

Why ``--check`` regenerates into a temporary directory and diffs the files
rather than comparing in memory: it exercises the same writer that
``schema-export`` uses, so a bug in writing cannot hide behind a passing check.
"""

import argparse
import difflib
import json
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from aimpire.contracts.mind import CONTRACT_VERSION, MindReply, Observation

_MODELS: dict[str, type[BaseModel]] = {
    f"mind-{CONTRACT_VERSION}.reply.schema.json": MindReply,
    f"mind-{CONTRACT_VERSION}.observation.schema.json": Observation,
}


def render_schemas() -> dict[str, str]:
    """Return ``{file name: canonical JSON text}`` for every exported schema."""
    return {
        name: json.dumps(model.model_json_schema(mode="validation"), sort_keys=True, indent=2)
        + "\n"
        for name, model in sorted(_MODELS.items())
    }


def write_schemas(out_dir: Path) -> list[Path]:
    """Write every schema into ``out_dir`` (created if missing); return the paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, text in render_schemas().items():
        path = out_dir / name
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def check_schemas(schema_dir: Path) -> list[str]:
    """Regenerate into a temporary directory and diff against ``schema_dir``.

    Returns human-readable problems; an empty list means the committed files
    are current. Only files this module generates are compared.
    """
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aimpire-schema-") as tmp:
        for fresh in write_schemas(Path(tmp)):
            committed = schema_dir / fresh.name
            if not committed.is_file():
                problems.append(f"missing: {committed}")
                continue
            want = fresh.read_text(encoding="utf-8")
            have = committed.read_text(encoding="utf-8")
            if want != have:
                diff = difflib.unified_diff(
                    have.splitlines(keepends=True),
                    want.splitlines(keepends=True),
                    fromfile=f"committed/{fresh.name}",
                    tofile=f"generated/{fresh.name}",
                )
                problems.append("".join(diff))
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point. Exit code 1 means drift (``--check``)."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("schema_dir", type=Path, help="the repository's schema/ directory")
    parser.add_argument("--check", action="store_true", help="fail if files differ")
    args = parser.parse_args(argv)
    schema_dir: Path = args.schema_dir
    if args.check:
        problems = check_schemas(schema_dir)
        for problem in problems:
            print(problem, file=sys.stderr)
        if problems:
            print("schema/ is stale: run `just schema-export`", file=sys.stderr)
            return 1
        print(f"schema/ is current ({len(_MODELS)} files)")
        return 0
    for path in write_schemas(schema_dir):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
