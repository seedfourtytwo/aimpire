#!/usr/bin/env python3
"""PostToolUse(Edit|Write): formats Python and flags oversized source files.

Layer: agent tooling. Reuses the limits in `tools/checks/repo_hygiene.py`
so the hook and CI can never disagree.

Must never: fail the session if ruff is missing (formatting is best-effort;
CI is the real gate).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from hook_io import emit, project_dir, read_event

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "checks"))
import repo_hygiene  # noqa: E402  (path set up above)


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
    ruff = shutil.which("ruff")
    if ruff and path.suffix == ".py":
        subprocess.run([ruff, "format", "--quiet", str(path)], check=False)


def main() -> int:
    """Hook entry point; always exits 0 so a hook bug never blocks the session."""
    event = read_event()
    raw = str(event.get("tool_input", {}).get("file_path", ""))
    if not raw:
        return 0
    root = project_dir(event)
    path = Path(raw) if Path(raw).is_absolute() else root / raw
    try:
        rel_path: str | None = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel_path = None  # file outside the project: check it without exemptions
    _format_python(path)
    message = size_feedback(path, rel_path)
    if message:
        emit({"decision": "block", "reason": message})
    return 0


if __name__ == "__main__":
    sys.exit(main())
