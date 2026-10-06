"""Shared pytest setup for repository tooling tests.

Makes `tools/checks` and `.claude/hooks` importable as plain modules so the
tests exercise exactly the code that CI and Claude Code hooks execute.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

for extra in (REPO_ROOT / "tools" / "checks", REPO_ROOT / ".claude" / "hooks"):
    sys.path.insert(0, str(extra))
