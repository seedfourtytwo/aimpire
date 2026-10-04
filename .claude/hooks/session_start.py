#!/usr/bin/env python3
"""SessionStart hook: injects project status and the session routine.

Layer: agent tooling. Guarantees every session (new, resumed or compacted)
starts from STATUS.md and the rules in AGENTS.md, even if the agent skips
reading them.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from hook_io import add_context, project_dir, read_event

STATUS_PATH = Path("docs/agents/STATUS.md")
STATUS_MAX_LINES = 40

ROUTINE = """\
Session routine (AGENTS.md §5.3 — mandatory):
1. Rules: AGENTS.md is canonical. Re-read the sections your task touches.
2. Confirm the issue/milestone and the acceptance check before coding.
3. Orchestrate the TDD loop with the agent team (CLAUDE.md "Agent team"):
   architect (plan) → test-writer (red) → implementer (green) → reviewer → scribe.
4. Finish with `just check` (real output) and /handoff."""


def build_context(root: Path, branch: str) -> str:
    """Compose the context block from STATUS.md, the branch and the routine."""
    status_file = root / STATUS_PATH
    if status_file.is_file():
        lines = status_file.read_text(encoding="utf-8").splitlines()[:STATUS_MAX_LINES]
        status = "\n".join(lines)
    else:
        status = f"{STATUS_PATH} not found — create it from docs/agents/workflow.md."
    return f"Branch: {branch}\n\n{ROUTINE}\n\n--- {STATUS_PATH} (head) ---\n{status}"


def _current_branch(root: Path) -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"], cwd=root, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() or "(detached or not a git repo)"


def main() -> int:
    """Hook entry point; always exits 0 so a hook bug never blocks the session."""
    event = read_event()
    root = project_dir(event)
    add_context("SessionStart", build_context(root, _current_branch(root)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
