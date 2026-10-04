#!/usr/bin/env python3
"""PreToolUse(Edit|Write) guard for the `implementer` subagent.

Layer: agent tooling. Enforces the TDD role split (AGENTS.md §5.1): the
implementer makes tests pass but may not edit tests, fixtures or golden
hashes. If a test looks wrong, it reports back instead of changing it.

Wired only in `.claude/agents/implementer.md`, never globally.
"""

from __future__ import annotations

import re
import sys

from hook_io import deny_tool, read_event

_PROTECTED = re.compile(
    r"(^|/)(tests?|e2e|fixtures)/"  # test, e2e and fixture directories
    r"|(^|/)test_[^/]*\.py$"  # pytest files
    r"|_test\.py$"
    r"|\.(test|spec)\.[jt]sx?$"  # vitest / playwright files
    r"|(^|/)conftest\.py$"
)


def is_protected_test_path(path: str) -> bool:
    """True if `path` is a test, fixture or golden file."""
    return bool(_PROTECTED.search(path.replace("\\", "/")))


def main() -> int:
    """Hook entry point; always exits 0 so a hook bug never blocks the session."""
    event = read_event()
    path = str(event.get("tool_input", {}).get("file_path", ""))
    if is_protected_test_path(path):
        deny_tool(
            "PreToolUse",
            "implementer may not edit tests or fixtures (TDD role split, AGENTS.md §5.1). "
            "If the test is wrong, stop and report why to the orchestrator.",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
