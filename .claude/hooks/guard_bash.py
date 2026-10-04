#!/usr/bin/env python3
"""PreToolUse(Bash) guard: blocks commands AGENTS.md §7 reserves for the creator.

Layer: agent tooling. Complements `permissions.deny` in settings.json (prefix
matching only). Rules run on parsed argv per command segment (`shell_words`),
so quoted text, commit messages and heredoc bodies do not trigger them.

Allowed on purpose: `git push --force-with-lease` to a feature branch (needed
after rebasing an open PR). Must never block routine work.
"""

from __future__ import annotations

import posixpath
import re
import sys
from collections.abc import Callable
from typing import Any

from hook_io import deny_tool, run_hook, tool_input
from shell_words import segments

Rule = Callable[[list[str]], str | None]

_LITERAL_KEY = re.compile(r"\bsk-(?:ant|proj|or)-[\w-]{12,}|\bsk-[A-Za-z0-9]{20,}")
_SECRET_NAME = re.compile(r"\w*(?:API_KEY|_TOKEN|SECRET|PASSWORD)\w*")
_SECRET_VAR = re.compile(r"\$\{?" + _SECRET_NAME.pattern)
_QUOTED_ENV_PATH = re.compile(r"[\"']([^\"']*/)?\.env(\.(?!example)[\w.-]+)?[\"']")
_GIT_OPTS_WITH_VALUE = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})
_COMMIT_OPTS_WITH_VALUE = frozenset({"-m", "-F", "-C", "-c", "--message", "--file", "--author"})

FORCE = (
    "Force-push (other than --force-with-lease to a feature branch) is reserved "
    "for the creator (AGENTS.md §7)."
)
MAIN = "Never push to main; open a PR from a feature branch (AGENTS.md §7)."
DELETE = "Deleting remote branches needs the creator's approval (AGENTS.md §7)."
NO_VERIFY = "Hooks and checks must not be skipped (AGENTS.md §5)."
DESTRUCTIVE = "Destructive git operations need the creator's approval (AGENTS.md §7)."
ENV_FILE = "Never read .env files or print credentials (AGENTS.md §8)."
LEAK = "Never print or inline credentials (AGENTS.md §8)."
PUBLISH = (
    "Publishing, merging, approving or changing visibility needs the creator (AGENTS.md §1.9, §7)."
)


def _short_flags(args: list[str]) -> str:
    """All letters from short-option clusters (`-uf` → `uf`)."""
    return "".join(a[1:] for a in args if a.startswith("-") and not a.startswith("--"))


def _git_subcommand(argv: list[str]) -> tuple[str, list[str]] | None:
    """(`push`, args) for `git [-C dir] push args`; None if not a git command."""
    if posixpath.basename(argv[0]) != "git":
        return None
    index = 1
    while index < len(argv) and argv[index].startswith("-"):
        index += 2 if argv[index] in _GIT_OPTS_WITH_VALUE else 1
    return (argv[index], argv[index + 1 :]) if index < len(argv) else None


def _push_reason(args: list[str]) -> str | None:
    refs = [a for a in args if not a.startswith("-")]
    long_force = [
        a for a in args if a.startswith("--force") and not a.startswith("--force-with-lease")
    ]
    if "--no-verify" in args:
        return NO_VERIFY
    if any(r.lstrip("+") == "main" or r.endswith((":main", "refs/heads/main")) for r in refs):
        return MAIN
    if (
        long_force
        or "f" in _short_flags(args)
        or "--mirror" in args
        or any(r.startswith("+") for r in refs)
    ):
        return FORCE
    if "--delete" in args or "d" in _short_flags(args) or any(r.startswith(":") for r in refs):
        return DELETE
    return None


def _commit_flags(args: list[str]) -> list[str]:
    flags, skip = [], False
    for arg in args:
        if not skip and arg.startswith("-"):
            flags.append(arg)
        skip = arg in _COMMIT_OPTS_WITH_VALUE and not skip
    return flags


def _git_reason(argv: list[str]) -> str | None:
    parsed = _git_subcommand(argv)
    if parsed is None:
        return None
    sub, args = parsed
    if sub == "push":
        return _push_reason(args)
    if sub == "commit":
        flags = _commit_flags(args)
        return NO_VERIFY if "--no-verify" in flags or "n" in _short_flags(flags) else None
    destructive = (
        (sub == "reset" and "--hard" in args)
        or (sub == "clean" and ("--force" in args or "f" in _short_flags(args)))
        or (sub == "checkout" and "." in args)
        or (sub == "restore" and "." in args and "--staged" not in args)
        or (sub == "branch" and "D" in _short_flags(args))
    )
    return DESTRUCTIVE if destructive else None


def _gh_reason(argv: list[str]) -> str | None:
    if posixpath.basename(argv[0]) != "gh":
        return None
    args = argv[1:]
    head = tuple(args[:2])
    risky = (
        head in {("release", "create"), ("repo", "delete"), ("pr", "merge")}
        or (head == ("repo", "edit") and any(a.startswith("--visibility") for a in args))
        or (head == ("pr", "review") and ("--approve" in args or "-a" in args))
        or (args[:1] == ["api"] and any(re.match(r"(private|visibility)=", a) for a in args))
    )
    return PUBLISH if risky else None


def _secret_reason(argv: list[str]) -> str | None:
    name = posixpath.basename(argv[0])
    if name in {"git", "gh"}:
        return None  # commit messages and PR text may mention variable names
    if argv == ["env"] or (
        name == "printenv" and (len(argv) == 1 or any(_SECRET_NAME.fullmatch(a) for a in argv[1:]))
    ):
        return LEAK
    if any(_SECRET_VAR.search(a) for a in argv):
        return LEAK
    for arg in argv:
        base = posixpath.basename(arg)
        if (
            re.fullmatch(r"\.env(\..+)?", base) and not base.startswith(".env.example")
        ) or _QUOTED_ENV_PATH.search(arg):
            return ENV_FILE
    return None


RULES: tuple[Rule, ...] = (_git_reason, _gh_reason, _secret_reason)


def deny_reason(command: str) -> str | None:
    """Return why `command` is blocked, or None if it may run."""
    if _LITERAL_KEY.search(command):
        return "Literal API keys must never appear in commands (AGENTS.md §8)."
    for argv in segments(command):
        for rule in RULES:
            reason = rule(argv)
            if reason:
                return reason
    return None


def handle(event: dict[str, Any]) -> None:
    """Deny the Bash call if any segment breaks a rule."""
    reason = deny_reason(str(tool_input(event).get("command", "")))
    if reason:
        deny_tool("PreToolUse", f"Blocked by .claude/hooks/guard_bash.py: {reason}")


if __name__ == "__main__":
    sys.exit(run_hook(handle))
