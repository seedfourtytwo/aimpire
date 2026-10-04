#!/usr/bin/env python3
"""Stop hook: reminds once per session to update STATUS.md after code changes.

Layer: agent tooling. Enforces the session routine (AGENTS.md §5.3). It
reminds rather than blocks, and only once per session (marker file), so it
cannot trap Claude in a loop.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from hook_io import add_context, project_dir, read_event

STATUS_PATH = "docs/agents/STATUS.md"
# Changes under these prefixes count as "work" that STATUS.md should reflect.
_WORK_PREFIXES = (
    "sim/",
    "client/",
    "rules/",
    "scenarios/",
    "profiles/",
    "schema/",
    "fixtures/",
    "tools/",
    "evals/",
    ".claude/",
    "ci/",
    ".github/",
)


def needs_status_reminder(changed: list[str]) -> bool:
    """True if work files changed but STATUS.md did not."""
    touched_work = any(path.startswith(_WORK_PREFIXES) for path in changed)
    return touched_work and STATUS_PATH not in changed


def _changed_files(root: Path) -> list[str]:
    """Files changed on this branch vs origin/main, plus uncommitted ones."""
    commands = (
        ["git", "diff", "--name-only", "origin/main...HEAD"],
        ["git", "diff", "--name-only", "HEAD"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    )
    changed: set[str] = set()
    for command in commands:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        changed.update(line for line in result.stdout.splitlines() if line)
    return sorted(changed)


def main() -> int:
    """Hook entry point; always exits 0 so a hook bug never blocks the session."""
    event = read_event()
    if event.get("stop_hook_active"):
        return 0
    marker = Path(tempfile.gettempdir()) / f"aimpire-status-reminded-{event.get('session_id', 'x')}"
    if marker.exists():
        return 0
    if needs_status_reminder(_changed_files(project_dir(event))):
        marker.touch()
        add_context(
            "Stop",
            f"Code changed on this branch but {STATUS_PATH} did not. Before ending the "
            "session, run /handoff (update STATUS.md, write a handoff note if work remains).",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
