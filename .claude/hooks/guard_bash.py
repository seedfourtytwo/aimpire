#!/usr/bin/env python3
"""PreToolUse(Bash) guard: blocks commands AGENTS.md §1/§7 reserve for the creator.

Layer: agent tooling. Complements `permissions.deny` in settings.json, which
matches prefixes only; this guard matches anywhere in compound commands.

Must never: block routine work (tests, just recipes, pushing feature branches).
"""

from __future__ import annotations

import re
import sys

from hook_io import deny_tool, read_event

# (pattern, reason). Patterns are searched, so they also catch `a && b` chains.
_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\bgit\s+push\b[^;&|]*\s(--force\S*|-f)\b"),
        "Force-push is reserved for the creator (AGENTS.md §7).",
    ),
    (
        re.compile(r"\bgit\s+push\b[^;&|]*\s(\S+:)?main\b"),
        "Never push to main; open a PR from a feature branch (AGENTS.md §7).",
    ),
    (re.compile(r"--no-verify\b"), "Hooks and checks must not be skipped (AGENTS.md §5)."),
    (
        re.compile(r"\bgit\s+(reset\s+--hard|clean\s+-\w*f)"),
        "Destructive git operations need the creator's approval (AGENTS.md §7).",
    ),
    (
        re.compile(
            r"(^|[\s;&|<])(cat|less|more|head|tail|source|\.)\s+[^;&|]*\.env(\.(?!example)\S+)?(\s|$)"
        ),
        "Never read .env files or print credentials (AGENTS.md §8).",
    ),
    (
        re.compile(r"\b(sk-ant-[A-Za-z0-9_-]{8,}|sk-[A-Za-z0-9]{20,})"),
        "Literal API keys must never appear in commands (AGENTS.md §8).",
    ),
    (
        re.compile(r"\bgh\s+(release\s+create|repo\s+edit[^;&|]*--visibility)"),
        "Publishing releases or changing visibility needs creator approval (AGENTS.md §1.9).",
    ),
)


def deny_reason(command: str) -> str | None:
    """Return why `command` is blocked, or None if it may run."""
    for pattern, reason in _RULES:
        if pattern.search(command):
            return reason
    return None


def main() -> int:
    """Hook entry point; always exits 0 so a hook bug never blocks the session."""
    event = read_event()
    command = str(event.get("tool_input", {}).get("command", ""))
    reason = deny_reason(command)
    if reason:
        deny_tool("PreToolUse", f"Blocked by .claude/hooks/guard_bash.py: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
