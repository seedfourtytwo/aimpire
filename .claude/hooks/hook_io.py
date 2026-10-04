"""Shared stdin/stdout helpers for Claude Code hook scripts.

Layer: agent tooling (stdlib only). Hook contract per Claude Code docs
(https://code.claude.com/docs/en/hooks, checked 2026-10-04): the event arrives
as JSON on stdin; JSON on stdout with exit code 0 carries decisions/context.

Must never: print secrets or tool input back verbatim, or crash. Every hook
runs through `run_hook`, which fails open (exit 0, note on stderr): a broken
guardrail must not stop the session — CI remains the real gate.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any


def read_event() -> dict[str, Any]:
    """Return the hook event JSON, or an empty dict if stdin is empty/invalid."""
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def tool_input(event: dict[str, Any]) -> dict[str, Any]:
    """The event's `tool_input` object, or `{}` if it is missing or not an object."""
    value = event.get("tool_input")
    return value if isinstance(value, dict) else {}


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


def run_hook(handler: Callable[[dict[str, Any]], None]) -> int:
    """Read the event, run `handler`, and always return exit code 0.

    Args:
        handler: Hook body; receives the parsed event and writes any response.

    Returns:
        0, even if the handler raised (the error goes to stderr).
    """
    try:
        handler(read_event())
    except Exception as error:  # noqa: BLE001 — fail open by design (module docstring)
        print(f"hook {Path(sys.argv[0]).name} failed open: {error!r}", file=sys.stderr)  # noqa: T201
    return 0
