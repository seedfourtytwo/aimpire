#!/usr/bin/env python3
"""PreToolUse(Edit|Write|NotebookEdit) guard for the `implementer` subagent.

Layer: agent tooling. Enforces the TDD role split (AGENTS.md §5.1): the
implementer makes tests pass but may not edit tests, fixtures, snapshots,
test-runner config, or the guardrails themselves (hooks, agents, ruff limits,
CI). If a test looks wrong, it reports back instead of changing it.

Wired only in `.claude/agents/implementer.md`, never globally.
"""

from __future__ import annotations

import posixpath
import re
import sys
from pathlib import Path
from typing import Any

from hook_io import deny_tool, project_dir, run_hook, tool_input

_PROTECTED = re.compile(
    r"(^|/)(tests?|e2e|fixtures|__tests__|__snapshots__)/"  # test and fixture dirs
    r"|-snapshots/"  # Playwright visual baselines
    r"|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$"  # pytest
    r"|\.(test|spec)\.[cm]?[jt]sx?$"  # vitest / playwright specs
    r"|(^|/)(vitest|playwright)\.config\.[cm]?[jt]s$"  # runner config and thresholds
    r"|^\.claude/|^\.github/|^ci/|^tools/checks/|^ruff\.toml$"  # the guardrails themselves
)


def project_relative(path: str, root: Path) -> str:
    """Normalize `path` and make it relative to `root` when it lies inside it."""
    normalized = posixpath.normpath(path.replace("\\", "/"))
    candidate = Path(normalized)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return normalized
    return normalized


def is_protected_test_path(path: str) -> bool:
    """True if repo-relative `path` is a test, fixture, snapshot or guardrail file."""
    return bool(_PROTECTED.search(posixpath.normpath(path.replace("\\", "/"))))


def handle(event: dict[str, Any]) -> None:
    """Deny edits to protected paths."""
    data = tool_input(event)
    raw = str(data.get("file_path") or data.get("notebook_path") or "")
    if raw and is_protected_test_path(project_relative(raw, project_dir(event))):
        deny_tool(
            "PreToolUse",
            "implementer may not edit tests, fixtures, snapshots, runner config or guardrails "
            "(TDD role split, AGENTS.md §5.1). If a test is wrong, stop and report why.",
        )


if __name__ == "__main__":
    sys.exit(run_hook(handle))
