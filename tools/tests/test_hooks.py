"""Tests for the pure logic of the Claude Code hooks in `.claude/hooks/`.

The Bash guard has its own file (`test_guard_bash.py`); end-to-end script
runs are in `test_hook_scripts.py`.
"""

from __future__ import annotations

from pathlib import Path

import guard_tests
import hook_io
import post_edit_check
import pytest
import session_start
import stop_check

# --- guard_tests ------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "sim/tests/unit/test_rng.py",
        "sim/src/aimpire/sim/rng_test.py",
        "client/web/src/map/projection.test.ts",
        "client/web/src/map/projection.test.mts",
        "client/web/src/__tests__/map.tsx",
        "client/web/e2e/map.spec.ts",
        "client/web/e2e/map.spec.ts-snapshots/map-chromium.png",
        "client/web/src/__snapshots__/x.snap",
        "client/web/vitest.config.ts",
        "client/web/playwright.config.ts",
        "fixtures/golden/shared_river.json",
        "sim/tests/conftest.py",
        ".claude/hooks/guard_tests.py",
        ".claude/agents/implementer.md",
        "ruff.toml",
        "tools/checks/repo_hygiene.py",
        "ci/workflows/ci.yml",
        ".github/workflows/ci.yml",
        "sim/pyproject.toml",
        "client/web/vite.config.ts",
        "client/web/package.json",
        "client/web/eslint.config.js",
        "sim/.coveragerc",
        "justfile",
        "AGENTS.md",
        "CLAUDE.md",
        ".pre-commit-config.yaml",
        ".gitignore",
    ],
)
def test_test_fixture_and_guardrail_paths_are_protected(path: str) -> None:
    assert guard_tests.is_protected_test_path(path)


@pytest.mark.parametrize(
    "path",
    [
        "sim/src/aimpire/sim/rng.py",
        "client/web/src/map/projection.ts",
        "docs/testing.md",
        "sim/tests/../src/aimpire/sim/x.py",
    ],
)
def test_production_paths_are_not_protected(path: str) -> None:
    assert not guard_tests.is_protected_test_path(path)


def test_absolute_paths_are_relativized_to_the_project(tmp_path: Path) -> None:
    root = tmp_path / "tests" / "aimpire"  # repo living under a dir named tests/
    assert guard_tests.project_relative(str(root / "sim/src/a.py"), root) == "sim/src/a.py"
    outside = guard_tests.project_relative("/elsewhere/tests/a.py", root)
    assert outside == "/elsewhere/tests/a.py"


# --- hook_io ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "event", [{}, {"tool_input": None}, {"tool_input": "x"}, {"tool_input": []}]
)
def test_tool_input_is_always_a_dict(event: dict[str, object]) -> None:
    assert hook_io.tool_input(event) == {}


# --- post_edit_check --------------------------------------------------------------


def test_post_edit_flags_file_over_hard_limit(tmp_path: Path) -> None:
    path = tmp_path / "big.py"
    path.write_text("x = 1\n" * 600, encoding="utf-8")
    message = post_edit_check.size_feedback(path)
    assert message is not None and "600" in message


def test_post_edit_is_silent_for_small_file(tmp_path: Path) -> None:
    path = tmp_path / "small.py"
    path.write_text("x = 1\n", encoding="utf-8")
    assert post_edit_check.size_feedback(path) is None


def test_post_edit_respects_generated_exemption(tmp_path: Path) -> None:
    path = tmp_path / "types.ts"
    path.write_text("x;\n" * 900, encoding="utf-8")
    assert post_edit_check.size_feedback(path, "client/web/src/contract/types.ts") is None


# --- stop_check -------------------------------------------------------------------


def test_stop_reminds_when_code_changed_without_status() -> None:
    assert stop_check.needs_status_reminder(["sim/src/aimpire/sim/rng.py"])


def test_stop_silent_when_status_updated() -> None:
    changed = ["sim/src/aimpire/sim/rng.py", "docs/agents/STATUS.md"]
    assert not stop_check.needs_status_reminder(changed)


def test_stop_silent_when_branch_handoff_written() -> None:
    changed = ["sim/src/aimpire/sim/rng.py", "docs/agents/handoff-agent-12-rng.md"]
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


def test_handoff_slug_flattens_branch_names() -> None:
    assert session_start.handoff_path("agent/12-rng") == "docs/agents/handoff-agent-12-rng.md"
