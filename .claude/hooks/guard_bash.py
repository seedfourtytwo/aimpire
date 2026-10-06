#!/usr/bin/env python3
"""PreToolUse(Bash) guard: blocks commands AGENTS.md §7 reserves for the creator.

Layer: agent tooling. Complements `permissions.deny` in settings.json (prefix
matching only). Rules run on parsed commands (`shell_words`), recurse into
`bash -c`/`sh -c`/`eval` strings and command substitutions, and ignore quoted
text, commit messages and heredoc bodies.

Allowed on purpose: `git push --force-with-lease` to a feature branch (needed
after rebasing an open PR), read-only `gh api`. Must never block routine work.
"""

from __future__ import annotations

import posixpath
import re
import subprocess
import sys
from typing import Any

from git_rules import NO_VERIFY, BranchLookup, git_reason
from hook_io import deny_tool, project_dir, run_hook, tool_input
from shell_words import Command, commands

_LITERAL_KEY = re.compile(r"(?<![\w-])sk-(?:ant|proj|or)-[\w-]{12,}|(?<![\w-])sk-[A-Za-z0-9]{20,}")
_SECRET_SUFFIX = r"(?:API_KEY|_TOKEN|SECRET|PASSWORD)"  # noqa: S105 — a name pattern, not a credential
_SECRET_NAME = re.compile(r"\w*" + _SECRET_SUFFIX)
_SECRET_VAR = re.compile(r"\$\{?\w*" + _SECRET_SUFFIX + r"(?!\w)")
_ENV_FILE = re.compile(r"\.env(\.[\w.*?-]+|\*)?")
_QUOTED_ENV_PATH = re.compile(r"[\"']([^\"']*/)?\.env(\.(?!example)[\w.-]+)?[\"']")
_SHELLS = frozenset({"bash", "sh", "zsh", "dash"})
_ENV_SAFE_COMMANDS = frozenset({"test", "[", "rm", "touch", "ls", "git", "gh"})
_PATTERN_FIRST = frozenset({"grep", "rg", "egrep", "fgrep"})
_GH_READ_METHODS = frozenset({"GET", "HEAD"})
_GH_FIELD_FLAGS = frozenset({"-f", "-F", "--field", "--raw-field", "--input"})
_MAX_DEPTH = 3

LEAK = "Never print or inline credentials (AGENTS.md §8)."
ENV_FILE = "Never read .env files (AGENTS.md §8)."
PUBLISH = (
    "Publishing, merging, approving, API writes or live workflows need the creator (AGENTS.md §7)."
)


def _gh_api_writes(args: list[str]) -> bool:
    """True if a `gh api` call can change state (non-GET, or fields without -X GET)."""
    method = None
    for index, arg in enumerate(args):
        if arg in {"-X", "--method"} and index + 1 < len(args):
            method = args[index + 1].upper()
        elif arg.startswith(("-X", "--method=")) and len(arg) > len("-X"):
            method = arg.split("=", 1)[-1].removeprefix("-X").upper()
    if args[:1] == ["graphql"]:
        return any("mutation" in a for a in args)
    has_fields = any(a in _GH_FIELD_FLAGS for a in args)
    return (method or ("POST" if has_fields else "GET")) not in _GH_READ_METHODS


def _gh_reason(argv: list[str]) -> str | None:
    if posixpath.basename(argv[0]) != "gh":
        return None
    args = argv[1:]
    head = tuple(args[:2])
    risky = (
        head in {("release", "create"), ("repo", "delete"), ("pr", "merge"), ("workflow", "run")}
        or (head == ("repo", "edit") and any(a.startswith("--visibility") for a in args))
        or (head == ("pr", "review") and ("--approve" in args or "-a" in args))
        or (args[:1] == ["api"] and _gh_api_writes(args[1:]))
    )
    return PUBLISH if risky else None


def _env_file_args(argv: list[str]) -> list[str]:
    """Arguments that a command would *read* as files."""
    name = posixpath.basename(argv[0])
    args = [a.lstrip("<") for a in argv[1:]]
    if name in _ENV_SAFE_COMMANDS:
        return []
    if name in {"cp", "mv"}:
        return args[:-1]  # the last argument is the destination
    if name in _PATTERN_FIRST:
        positional = [a for a in args if not a.startswith("-")]
        return positional[1:]
    return args


def _secret_reason(argv: list[str]) -> str | None:
    name = posixpath.basename(argv[0])
    if name in {"git", "gh"}:
        return None  # commit messages and PR text may mention variable names
    names = argv[1:]
    if argv == ["env"] or (
        name == "printenv" and (not names or any(_SECRET_NAME.fullmatch(a) for a in names))
    ):
        return LEAK
    if name not in {"test", "["} and any(_SECRET_VAR.search(a) for a in argv):
        return LEAK  # `test -n "$KEY"` only checks presence and prints nothing
    for arg in _env_file_args(argv):
        base = posixpath.basename(arg)
        if (
            _ENV_FILE.fullmatch(base) and not base.startswith(".env.example")
        ) or _QUOTED_ENV_PATH.search(arg):
            return ENV_FILE
    return None


def _nested_script(argv: list[str]) -> str | None:
    """The script string run by `bash -c STR` (also `-lc`, `-ec`, ...) or `eval STR`."""
    name = posixpath.basename(argv[0])
    if name == "eval":
        return " ".join(argv[1:])
    if name not in _SHELLS:
        return None
    for index, arg in enumerate(argv[1:-1], start=1):
        if arg.startswith("-") and not arg.startswith("--") and "c" in arg[1:]:
            return argv[index + 1]
    return None


def _command_reason(command: Command, current_branch: BranchLookup, depth: int) -> str | None:
    if any(v.startswith("SKIP=") for v in command.env):
        return NO_VERIFY  # prek/pre-commit skips named hooks
    if not command.argv:
        return None
    nested = _nested_script(command.argv)
    if nested is not None and depth < _MAX_DEPTH:
        return deny_reason(nested, current_branch, depth + 1)
    return (
        git_reason(command.argv, current_branch)
        or _gh_reason(command.argv)
        or _secret_reason(command.argv)
    )


def deny_reason(
    command: str, current_branch: BranchLookup = lambda: None, depth: int = 0
) -> str | None:
    """Return why `command` is blocked, or None if it may run.

    Args:
        command: The Bash command string Claude wants to run.
        current_branch: Returns the checked-out branch (None if unknown); used for implicit pushes.
        depth: Recursion depth for nested shells (internal).
    """
    if _LITERAL_KEY.search(command):
        return "Literal API keys must never appear in commands (AGENTS.md §8)."
    for parsed in commands(command):
        reason = _command_reason(parsed, current_branch, depth)
        if reason:
            return reason
    return None


def _branch_lookup(event: dict[str, Any]) -> BranchLookup:
    def lookup() -> str | None:
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=project_dir(event),
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return result.stdout.strip() or None

    return lookup


def handle(event: dict[str, Any]) -> None:
    """Deny the Bash call if any command in it breaks a rule."""
    reason = deny_reason(str(tool_input(event).get("command", "")), _branch_lookup(event))
    if reason:
        deny_tool("PreToolUse", f"Blocked by .claude/hooks/guard_bash.py: {reason}")


if __name__ == "__main__":
    sys.exit(run_hook(handle))
