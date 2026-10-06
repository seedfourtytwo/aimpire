"""End-to-end tests: run each hook script as Claude Code does (JSON on stdin).

Checks the real contract: exit code 0 always (hooks fail open), and stdout is
either empty or valid JSON in the documented shape. Malformed input and a
missing `git` must not crash a hook.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS = REPO_ROOT / ".claude" / "hooks"
SCRIPTS = ["guard_bash", "post_edit_check", "session_start", "stop_check"]


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
    assert "ADR-0022" in decision["permissionDecisionReason"]


def test_guard_bash_is_silent_when_allowed() -> None:
    assert run_hook("guard_bash", json.dumps({"tool_input": {"command": "just check"}})) == (0, "")


def _implementer_hook_command() -> str:
    """The PreToolUse command declared in the implementer agent's frontmatter."""
    text = (REPO_ROOT / ".claude" / "agents" / "implementer.md").read_text(encoding="utf-8")
    frontmatter = text.split("---")[1]
    match = re.search(r"command:\s*(.+)", frontmatter)
    assert match, "implementer.md must declare a PreToolUse hook command"
    return match.group(1).strip()


@pytest.mark.parametrize(
    ("target", "blocked"),
    [
        ("sim/tests/acceptance/test_example.py", True),
        ("CLAUDE.md", True),
        ("sim/ruff.toml", True),
        ("ruff.toml", True),
        (".pre-commit-config.yaml", True),
        ("tools/checks/hygiene-baseline.txt", True),
        ("tools/checks/repo_hygiene.py", True),
        ("sim/tests/unit/test_new_helper.py", False),
        ("sim/src/aimpire/sim/example.py", False),
    ],
)
def test_implementer_cannot_edit_protected_paths_even_when_session_allows(
    target: str, blocked: bool
) -> None:
    # A planning session may set AIMPIRE_ALLOW_PROTECTED=1; the implementer must not inherit it.
    event = {"tool_name": "Edit", "tool_input": {"file_path": str(REPO_ROOT / target)}}
    result = subprocess.run(
        ["bash", "-c", _implementer_hook_command()],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(REPO_ROOT), "AIMPIRE_ALLOW_PROTECTED": "1"},
    )
    assert (result.returncode == 2) == blocked, (target, result.stderr)


def test_session_start_injects_context() -> None:
    _, out = run_hook("session_start", '{"source": "startup"}')
    context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "Session routine" in context


def test_post_edit_check_blocks_oversized_file(tmp_path: Path) -> None:
    big = tmp_path / "big.py"
    big.write_text("x = 1\n" * 520, encoding="utf-8")
    _, out = run_hook("post_edit_check", json.dumps({"tool_input": {"file_path": str(big)}}))
    assert json.loads(out)["decision"] == "block"
