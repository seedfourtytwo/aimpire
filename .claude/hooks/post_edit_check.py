#!/usr/bin/env python3
"""PostToolUse(Edit|Write): formats Python and flags oversized source files.

Layer: agent tooling. Reuses the limits in `tools/checks/repo_hygiene.py`
so the hook and CI can never disagree, and the same pinned ruff as `just`.

Must never: touch files outside the project, or fail the session if uv/ruff
is missing (formatting is best-effort; CI is the real gate).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from hook_io import emit, project_dir, run_hook, tool_input

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "checks"))
import repo_hygiene  # noqa: E402  (path set up above)

RUFF = "ruff@0.16.10"  # keep in sync with `ruff` in the justfile


def size_feedback(path: Path, rel_path: str | None = None) -> str | None:
    """Message for Claude if `path` breaks the hard line limit, else None.

    `rel_path` (repo-relative) lets generated-file exemptions apply exactly as in CI.
    """
    if not path.is_file():
        return None
    violation = repo_hygiene.check_lines(rel_path or path.name, path)
    if violation and violation.is_error:
        return f"{path}: {violation.message} (AGENTS.md §4.1). Split it before continuing."
    return None


def _format_python(path: Path) -> None:
    uvx = shutil.which("uvx")
    if uvx and path.suffix == ".py":
        subprocess.run([uvx, RUFF, "format", "--quiet", str(path)], check=False, timeout=60)


def _relative(path: Path, root: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None  # outside the project


def handle(event: dict[str, Any]) -> None:
    """Format the edited Python file (in-project only) and flag size violations."""
    raw = str(tool_input(event).get("file_path", ""))
    if not raw:
        return
    root = project_dir(event)
    path = Path(raw) if Path(raw).is_absolute() else root / raw
    rel_path = _relative(path, root)
    if rel_path is not None:
        _format_python(path)
    message = size_feedback(path, rel_path)
    if message:
        emit({"decision": "block", "reason": message})


if __name__ == "__main__":
    sys.exit(run_hook(handle))
