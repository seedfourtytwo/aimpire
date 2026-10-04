"""Tests for Claude Code hook logic in `.claude/hooks/`.

Hooks are thin wrappers around pure functions; only the pure functions are
tested here, so the tests need no Claude Code runtime.
"""

from __future__ import annotations

from pathlib import Path

import guard_bash
import guard_tests
import post_edit_check
import pytest
import session_start
import stop_check

# --- guard_bash -----------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "git push --force origin feat/x",
        "git push -f",
        "git push --force-with-lease",
        "git push origin main",
        "git push origin HEAD:main",
        "git commit --no-verify -m wip",
        "git reset --hard origin/main",
        "git clean -fdx",
        "cat .env",
        "source .env.local && just test",
        "curl -H 'x-api-key: sk-ant-api03-abcdefghijklmnop' https://api.anthropic.com",
        "gh release create v0.1.0",
        "gh repo edit --visibility public",
    ],
)
def test_guard_bash_denies_dangerous_commands(command: str) -> None:
    assert guard_bash.deny_reason(command) is not None


@pytest.mark.parametrize(
    "command",
    [
        "just check",
        "git push -u origin agent/12-rng",
        "git status",
        "uv run pytest -q",
        "git commit -m 'feat(sim): counter rng'",
        "grep -r mainland docs/",
        "cp .env.example .env.example.bak",
    ],
)
def test_guard_bash_allows_normal_commands(command: str) -> None:
    assert guard_bash.deny_reason(command) is None


# --- guard_tests ------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "sim/tests/unit/test_rng.py",
        "/repo/sim/src/aimpire/sim/rng_test.py",
        "client/web/src/map/projection.test.ts",
        "client/web/e2e/map.spec.ts",
        "fixtures/golden/shared_river.json",
        "sim/tests/conftest.py",
    ],
)
def test_test_and_fixture_paths_are_protected(path: str) -> None:
    assert guard_tests.is_protected_test_path(path)


@pytest.mark.parametrize(
    "path",
    ["sim/src/aimpire/sim/rng.py", "client/web/src/map/projection.ts", "docs/testing.md"],
)
def test_production_paths_are_not_protected(path: str) -> None:
    assert not guard_tests.is_protected_test_path(path)


# --- post_edit_check ----------------------------------------------------------------


def test_post_edit_flags_file_over_hard_limit(tmp_path: Path) -> None:
    path = tmp_path / "big.py"
    path.write_text("x = 1\n" * 600, encoding="utf-8")
    message = post_edit_check.size_feedback(path)
    assert message is not None and "600" in message


def test_post_edit_is_silent_for_small_file(tmp_path: Path) -> None:
    path = tmp_path / "small.py"
    path.write_text("x = 1\n", encoding="utf-8")
    assert post_edit_check.size_feedback(path) is None


# --- stop_check -------------------------------------------------------------------


def test_stop_reminds_when_code_changed_without_status() -> None:
    assert stop_check.needs_status_reminder(["sim/src/aimpire/sim/rng.py"])


def test_stop_silent_when_status_updated() -> None:
    changed = ["sim/src/aimpire/sim/rng.py", "docs/agents/STATUS.md"]
    assert not stop_check.needs_status_reminder(changed)


def test_stop_silent_for_docs_only_changes() -> None:
    assert not stop_check.needs_status_reminder(["docs/research/10-client-rendering.md"])


# --- session_start ----------------------------------------------------------------


def test_session_context_includes_status_and_routine(tmp_path: Path) -> None:
    status = tmp_path / "docs" / "agents" / "STATUS.md"
    status.parent.mkdir(parents=True)
    status.write_text("# Project status\n**Phase:** 1\n", encoding="utf-8")
    context = session_start.build_context(tmp_path, branch="agent/1-x")
    assert "**Phase:** 1" in context
    assert "agent/1-x" in context
    assert "AGENTS.md" in context


def test_session_context_survives_missing_status(tmp_path: Path) -> None:
    context = session_start.build_context(tmp_path, branch="main")
    assert "STATUS.md not found" in context
