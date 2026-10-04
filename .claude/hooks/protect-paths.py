#!/usr/bin/env python3
"""Claude Code hook: keep implementing sessions out of protected paths (ADR-0016).

Two modes, chosen by the first argument:

  pre   PreToolUse on Edit / Write / NotebookEdit. Reads the hook payload on
        stdin and exits 2 (block, with a message for the model) when the
        target file is protected. Creating a *new* file under docs/adr/ is
        allowed, because any agent may propose an ADR.

  stop  Stop hook. Lists protected files changed on this branch or in the
        working tree, as a message to the user. It never blocks: shell
        commands can bypass the pre hook, so this is the second line of
        defence, and the CI path check is the third.

Sessions that are meant to edit protected files (the strong-model session
writing acceptance tests or ADRs, or the creator) start Claude Code with
AIMPIRE_ALLOW_PROTECTED=1. Standard library only.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Keep this list identical to CLAUDE.md "Protected paths" and the CI check.
PROTECTED = re.compile(
    r"^(sim/tests/acceptance/|fixtures/golden/|\.github/|\.claude/|docs/adr/|CLAUDE\.md$)"
)
# Lint, type-check and import-rule settings live in their own files so they can
# be protected without blocking ordinary dependency changes in pyproject.toml.
PROTECTED_FILES = {"sim/ruff.toml", "sim/pyrightconfig.json", "sim/.importlinter"}
NEW_FILE_OK = re.compile(r"^docs/adr/\d{4}-[a-z0-9-]+\.md$")


def _git_toplevel(cwd: Path) -> Path | None:
    out = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=False,
    )
    top = out.stdout.strip()
    return Path(top).resolve() if out.returncode == 0 and top else None


def repo_root(near: str | None = None) -> Path:
    """The checkout that contains ``near`` (a file path or directory).

    Why not just CLAUDE_PROJECT_DIR: agent worktrees live under
    ``.claude/worktrees/<id>/`` inside the main checkout, while
    CLAUDE_PROJECT_DIR still names the main checkout. Measured from there,
    every worktree file starts with ``.claude/`` and would be blocked. So the
    root is found from the target's own nearest existing directory first.
    """
    if near:
        d = Path(near)
        if not d.is_absolute():
            d = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".") / d
        d = d.resolve()
        while not d.is_dir() and d != d.parent:
            d = d.parent
        top = _git_toplevel(d)
        if top:
            return top
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return _git_toplevel(Path.cwd()) or Path(".").resolve()


def relative(path: str, root: Path) -> str | None:
    """Repo-relative POSIX path, or None if the file is outside the repo."""
    p = Path(path)
    if not p.is_absolute():
        p = root / p
    try:
        return p.resolve().relative_to(root).as_posix()
    except ValueError:
        return None


def is_protected(rel: str) -> bool:
    return bool(PROTECTED.match(rel)) or rel in PROTECTED_FILES


def pre(payload: dict) -> int:
    if os.environ.get("AIMPIRE_ALLOW_PROTECTED") == "1":
        return 0
    tool_input = payload.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not target:
        return 0
    root = repo_root(target)
    rel = relative(target, root)
    if rel is None or not is_protected(rel):
        return 0
    if NEW_FILE_OK.match(rel) and not (root / rel).exists():
        return 0  # a new Proposed ADR
    print(
        f"Blocked: {rel} is a protected path (ADR-0016, CLAUDE.md). "
        "Implementing sessions do not change acceptance tests, golden fixtures, "
        "CI, agent settings, existing ADRs, CLAUDE.md or tool settings. "
        "If a test or rule seems wrong, stop and explain it in the pull request.",
        file=sys.stderr,
    )
    return 2


def changed_files(root: Path) -> set[str]:
    files: set[str] = set()
    for args in (
        ["git", "diff", "--name-only", "origin/main...HEAD"],
        ["git", "diff", "--name-only", "HEAD"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ):
        out = subprocess.run(args, cwd=root, capture_output=True, text=True, check=False)
        files.update(line for line in out.stdout.splitlines() if line)
    return files


def stop(payload: dict) -> int:
    root = repo_root(payload.get("cwd") or os.getcwd())
    touched = sorted(f for f in changed_files(root) if is_protected(f))
    if touched:
        msg = "Protected paths changed on this branch: " + ", ".join(touched)
        print(json.dumps({"systemMessage": msg}))
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre"
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    return pre(payload) if mode == "pre" else stop(payload)


if __name__ == "__main__":
    sys.exit(main())
