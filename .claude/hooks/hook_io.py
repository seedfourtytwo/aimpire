"""Shared stdin/stdout helpers for Claude Code hook scripts.

Layer: agent tooling (stdlib only). Hook contract per Claude Code docs
(https://code.claude.com/docs/en/hooks, checked 2026-10-04): the event arrives
as JSON on stdin; JSON on stdout with exit code 0 carries decisions/context.

Must never: print secrets or tool input back verbatim, or raise on bad input
(a crashing hook must not block the session; it fails open and says so).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


def read_event() -> dict[str, Any]:
    """Return the hook event JSON, or an empty dict if stdin is empty/invalid."""
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def project_dir(event: dict[str, Any]) -> Path:
    """Project root: $CLAUDE_PROJECT_DIR, else the event cwd, else the process cwd."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or Path.cwd())


def emit(payload: dict[str, Any]) -> None:
    """Write a hook JSON response to stdout."""
    json.dump(payload, sys.stdout)


def deny_tool(event_name: str, reason: str) -> None:
    """Deny a PreToolUse call with a reason Claude will see."""
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": event_name,
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def add_context(event_name: str, text: str) -> None:
    """Inject extra context for Claude (SessionStart/PostToolUse/Stop)."""
    emit({"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": text}})
