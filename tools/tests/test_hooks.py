"""Tests for the pure logic of the Claude Code hooks in `.claude/hooks/`.

The Bash guard has its own file (`test_guard_bash.py`); end-to-end script
runs are in `test_hook_scripts.py`.
"""

from __future__ import annotations

from pathlib import Path

import hook_io
import post_edit_check
import pytest
import session_start
import stop_check

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
    assert "CLAUDE.md" in context


def test_session_context_survives_missing_status(tmp_path: Path) -> None:
    context = session_start.build_context(tmp_path, branch="main")
    assert "STATUS.md not found" in context


def test_handoff_slug_flattens_branch_names() -> None:
    assert session_start.handoff_path("agent/12-rng") == "docs/agents/handoff-agent-12-rng.md"


@pytest.mark.parametrize(
    ("rel_path", "expected"),
    [
        ("tools/checks/repo_hygiene.py", True),
        (".claude/hooks/guard_bash.py", True),
        ("sim/src/aimpire/sim/rng.py", False),  # sim/ has its own locked ruff: `just fmt`
        ("docs/notes.py", False),
        (".claude/hooks/notes.md", False),
        (None, False),  # outside the project
    ],
)
def test_post_edit_formats_only_repo_tooling(rel_path: str | None, expected: bool) -> None:
    assert post_edit_check.should_format(rel_path) is expected
