#!/usr/bin/env python3
"""Stop hook: reminds once per session to record progress after code changes.

Layer: agent tooling. Enforces the session routine (AGENTS.md §5.3). Progress
counts as recorded when STATUS.md or a branch handoff note changed. It reminds
rather than blocks, and only once per session (marker file keyed by session
id; no marker without an id), so it cannot trap Claude in a loop.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from hook_io import add_context, project_dir, run_hook

STATUS_PATH = "docs/agents/STATUS.md"
HANDOFF_PREFIX = "docs/agents/handoff-"
# Changes under these prefixes count as "work" that should be recorded.
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
    """True if work files changed but neither STATUS.md nor a handoff note did."""
    touched_work = any(path.startswith(_WORK_PREFIXES) for path in changed)
    recorded = any(path == STATUS_PATH or path.startswith(HANDOFF_PREFIX) for path in changed)
    return touched_work and not recorded


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


def handle(event: dict[str, Any]) -> None:
    """Emit the reminder at most once per session."""
    session_id = event.get("session_id")
    if event.get("stop_hook_active") or not session_id:
        return
    marker = Path(tempfile.gettempdir()) / f"aimpire-status-reminded-{session_id}"
    if marker.exists() or not needs_status_reminder(_changed_files(project_dir(event))):
        return
    marker.touch()
    add_context(
        "Stop",
        f"Code changed but neither {STATUS_PATH} nor a handoff note did. Before ending the "
        "session, run /handoff.",
    )


if __name__ == "__main__":
    sys.exit(run_hook(handle))
