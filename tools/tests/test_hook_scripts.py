"""End-to-end tests: run each hook script as Claude Code does (JSON on stdin).

Checks the real contract: exit code 0 always (hooks fail open), and stdout is
either empty or valid JSON in the documented shape. Malformed input and a
missing `git` must not crash a hook.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS = REPO_ROOT / ".claude" / "hooks"
SCRIPTS = ["guard_bash", "guard_tests", "post_edit_check", "session_start", "stop_check"]


def run_hook(name: str, stdin: str, env_overrides: dict[str, str] | None = None) -> tuple[int, str]:
    """Run one hook script; return (exit code, stdout)."""
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(REPO_ROOT), **(env_overrides or {})}
    result = subprocess.run(
        [sys.executable, str(HOOKS / f"{name}.py")],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=30,
    )
    return result.returncode, result.stdout


@pytest.mark.parametrize("name", SCRIPTS)
@pytest.mark.parametrize("stdin", ["", "not json", "[]", '{"tool_input": null}', "{}"])
def test_hooks_fail_open_on_malformed_input(name: str, stdin: str) -> None:
    code, out = run_hook(name, stdin)
    assert code == 0
    if out.strip():
        json.loads(out)


@pytest.mark.parametrize("name", SCRIPTS)
def test_hooks_fail_open_without_git(name: str, tmp_path: Path) -> None:
    code, _ = run_hook(name, '{"session_id": "t"}', {"PATH": str(tmp_path)})
    assert code == 0


def test_guard_bash_emits_documented_deny_shape() -> None:
    event = {"tool_input": {"command": "git push --force"}}
    code, out = run_hook("guard_bash", json.dumps(event))
    decision = json.loads(out)["hookSpecificOutput"]
    assert code == 0
    assert decision["hookEventName"] == "PreToolUse"
    assert decision["permissionDecision"] == "deny"
    assert "AGENTS.md" in decision["permissionDecisionReason"]


def test_guard_bash_is_silent_when_allowed() -> None:
    assert run_hook("guard_bash", json.dumps({"tool_input": {"command": "just check"}})) == (0, "")


def test_guard_tests_reads_notebook_path() -> None:
    event = {"tool_input": {"notebook_path": "sim/tests/explore.ipynb"}}
    _, out = run_hook("guard_tests", json.dumps(event))
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_session_start_injects_context() -> None:
    _, out = run_hook("session_start", '{"source": "startup"}')
    context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "Session routine" in context


def test_post_edit_check_blocks_oversized_file(tmp_path: Path) -> None:
    big = tmp_path / "big.py"
    big.write_text("x = 1\n" * 520, encoding="utf-8")
    _, out = run_hook("post_edit_check", json.dumps({"tool_input": {"file_path": str(big)}}))
    assert json.loads(out)["decision"] == "block"
