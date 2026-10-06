#!/usr/bin/env python3
"""Repository hygiene gate: file size, source length and forbidden artifacts.

Layer: repo tooling (stdlib only, runs before any project venv exists).
Enforces AGENTS.md §4.1 ("no large files"). Function-level limits
(length, complexity, parameters) are enforced by ruff/eslint, not here.

Must never: modify files, call the network, or depend on third-party packages.

Usage:
    python3 tools/checks/repo_hygiene.py              # all tracked + new files
    python3 tools/checks/repo_hygiene.py path/a.py    # explicit paths
"""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Limits mirror AGENTS.md §4.1. Change both together.
SOURCE_LINE_TARGET = 300
SOURCE_LINE_HARD_LIMIT = 500
MAX_FILE_BYTES = 500 * 1024

SOURCE_SUFFIXES = frozenset(
    {".py", ".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs", ".css", ".sh"}
)

# Generated or vendored files: exempt from line limits (still size-checked).
GENERATED_GLOBS = ("schema/*", "client/web/src/contract/*", "*.generated.*")

# Legitimately large text files: exempt from the byte limit.
LARGE_FILE_ALLOWLIST = ("*.lock", "*package-lock.json", "schema/*")

# Never committed (AGENTS.md §1, §8): run data, weights, secrets.
FORBIDDEN_GLOBS = (
    "*.db",
    "*.db-wal",
    "*.db-shm",
    "*.sqlite",
    "*.sqlite3",
    "*.gguf",
    "*.safetensors",
    "*.ckpt",
    "*.pt",
    "*.onnx",
    ".env",
    ".env.*",
    "*/.env",
    "*/.env.*",
    "*.pem",
    "*.key",
    # run outputs: databases, blobs, saves, exports, logs (AGENTS.md §4.1)
    "runs/*",  # root-level run data only; source folders named `runs/` are fine
    "exports/*",
    "saves/*",
    "*.log",
    "*.zst",
)
# Golden fixtures are committed recorded runs (ADR-0004/0006); size limits still apply.
# Golden fixtures are committed recorded runs (ADR-0004/0006): run data only, size limits apply.
FORBIDDEN_EXCEPTIONS = (
    ".env.example",
    "*/.env.example",
    "fixtures/golden/*.db",
    "fixtures/golden/*.zst",
)


@dataclass(frozen=True)
class Violation:
    """One rule breach for one path."""

    path: str
    rule: str
    message: str
    is_error: bool = True

    def format(self) -> str:
        """Render as one human-readable report line."""
        level = "ERROR" if self.is_error else "warn "
        return f"{level} {self.path}: [{self.rule}] {self.message}"


def _matches(rel_path: str, globs: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(rel_path, pattern) for pattern in globs)


def _check_forbidden(rel_path: str) -> Violation | None:
    if _matches(rel_path, FORBIDDEN_GLOBS) and not _matches(rel_path, FORBIDDEN_EXCEPTIONS):
        return Violation(
            rel_path, "forbidden-file", "run data, weights or secrets must not be committed"
        )
    return None


def _check_bytes(rel_path: str, size: int) -> Violation | None:
    if size > MAX_FILE_BYTES and not _matches(rel_path, LARGE_FILE_ALLOWLIST):
        return Violation(
            rel_path, "file-too-large", f"{size // 1024} KB > {MAX_FILE_BYTES // 1024} KB"
        )
    return None


def check_lines(rel_path: str, path: Path) -> Violation | None:
    """Line-count check for source files; shared with the PostToolUse hook.

    Args:
        rel_path: Repo-relative path, used for generated-file exemptions.
        path: File to count.

    Returns:
        An error above the hard limit, a warning above target, else None.
    """
    if path.suffix not in SOURCE_SUFFIXES or _matches(rel_path, GENERATED_GLOBS):
        return None
    with path.open("rb") as handle:
        line_count = sum(1 for _ in handle)
    if line_count > SOURCE_LINE_HARD_LIMIT:
        return Violation(
            rel_path,
            "source-too-long",
            f"{line_count} lines > {SOURCE_LINE_HARD_LIMIT}; split by responsibility",
        )
    if line_count > SOURCE_LINE_TARGET:
        return Violation(
            rel_path,
            "source-over-target",
            f"{line_count} lines > target {SOURCE_LINE_TARGET}",
            is_error=False,
        )
    return None


def check_paths(root: Path, rel_paths: list[str]) -> list[Violation]:
    """Check repo-relative paths under `root`; missing paths are skipped."""
    violations: list[Violation] = []
    for rel_path in sorted(set(rel_paths)):
        path = root / rel_path
        if not path.is_file():
            continue
        forbidden = _check_forbidden(rel_path)
        if forbidden:
            violations.append(forbidden)
            continue
        for found in (_check_bytes(rel_path, path.stat().st_size), check_lines(rel_path, path)):
            if found:
                violations.append(found)
    return violations


def candidate_files(root: Path) -> list[str]:
    """Tracked files plus untracked-but-not-ignored ones (catches files before commit)."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    # -z: NUL-separated and unquoted, so non-ASCII names are not mangled.
    return [name for name in result.stdout.split("\0") if name]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 1 if any error-level violation exists."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("paths", nargs="*", help="repo-relative paths (default: all files)")
    args = parser.parse_args(argv)

    paths = args.paths or candidate_files(args.root)
    violations = check_paths(args.root, paths)
    for violation in violations:
        print(violation.format())
    errors = sum(1 for v in violations if v.is_error)
    print(f"repo-hygiene: {len(paths)} files, {errors} errors, {len(violations) - errors} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
