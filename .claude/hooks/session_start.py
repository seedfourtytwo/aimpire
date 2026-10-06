#!/usr/bin/env python3
"""SessionStart hook: injects project status and the session routine.

Layer: agent tooling. Guarantees every session (new, resumed, cleared or
compacted) starts from STATUS.md, the branch's handoff note and the routine in
CLAUDE.md, even if the agent skips reading them.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from hook_io import add_context, project_dir, run_hook

STATUS_PATH = Path("docs/agents/STATUS.md")
STATUS_MAX_LINES = 40

ROUTINE = """\
Session routine (CLAUDE.md, ADR-0016, ADR-0022):
1. Read STATUS (below), the issue or backlog entry, and the ADRs it names.
2. New backlog item: /spec (Opus architect + test-writer, acceptance tests first).
   Issue with acceptance tests: /build (Sonnet implementer, then Opus reviewer).
3. Never edit a test to make it pass. If a test seems wrong, stop and report it.
4. Finish with `just check` (real output); update STATUS.md or the branch handoff note."""


def handoff_path(branch: str) -> str:
    """Repo-relative handoff note path for `branch` (slashes flattened)."""
    return f"docs/agents/handoff-{branch.replace('/', '-')}.md"


def build_context(root: Path, branch: str) -> str:
    """Compose the context block from STATUS.md, the branch handoff and the routine."""
    status_file = root / STATUS_PATH
    if status_file.is_file():
        lines = status_file.read_text(encoding="utf-8").splitlines()[:STATUS_MAX_LINES]
        status = "\n".join(lines)
    else:
        status = f"{STATUS_PATH} not found — create it from docs/agents/workflow.md."
    handoff = root / handoff_path(branch)
    note = (
        f"\nHandoff note for this branch: {handoff_path(branch)} — read it first."
        if handoff.is_file()
        else ""
    )
    return f"Branch: {branch}{note}\n\n{ROUTINE}\n\n--- {STATUS_PATH} (head) ---\n{status}"


def _current_branch(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "(git unavailable)"
    return result.stdout.strip() or "(detached or not a git repo)"


def handle(event: dict[str, Any]) -> None:
    """Inject the session context."""
    root = project_dir(event)
    add_context("SessionStart", build_context(root, _current_branch(root)))


if __name__ == "__main__":
    sys.exit(run_hook(handle))
