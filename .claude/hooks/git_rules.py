"""Git command rules for the Bash guard (ADR-0022).

Layer: agent tooling (stdlib only). Pure functions over one argv list; no
I/O except through the injected `current_branch` callable.

Policy encoded here:
- never push to `main` (explicitly, or implicitly while on `main`), never
  `--all`/`--mirror`/`--prune`, never delete remote branches;
- the only allowed force is `--force-with-lease` (optionally with
  `--force-if-includes`) to a feature branch;
- never skip hooks (`--no-verify` and unambiguous prefixes, `commit -n`,
  `-c core.hooksPath=…`);
- never discard work (`reset --hard`, `clean -f`, `checkout -f|--|.`,
  `restore` of the worktree, `stash clear`, forced branch delete, `update-ref -d`).
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Callable

BranchLookup = Callable[[], str | None]

FORCE = (
    "Force-push (other than --force-with-lease to a feature branch) is reserved "
    "for the creator (ADR-0022)."
)
MAIN = "Never push to main; open a PR from a feature branch (ADR-0022)."
DELETE = "Deleting remote branches needs the creator's approval (ADR-0022)."
NO_VERIFY = "Hooks and checks must not be skipped (ADR-0022)."
DESTRUCTIVE = "Discarding work or history needs the creator's approval (ADR-0022)."
TAGS = "Pushing tags is part of releasing, which is the creator's call (ADR-0022)."

_GIT_OPTS_WITH_VALUE = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})
_SAFE_FORCE = ("--force-with-lease", "--force-if-includes")
_IMPLICIT_REFS = frozenset({"HEAD", "@"})
_TAG_REF = re.compile(r"(refs/tags/|v\d)")
_MIN_NO_VERIFY_PREFIX = len("--no-v")  # shortest unambiguous abbreviation git accepts here
# Short options whose value may be attached (`-m"msg"`, `-o"skip-ci"`): letters after them are data.
_PUSH_VALUE_LETTERS = frozenset("o")
_COMMIT_VALUE_LETTERS = frozenset("mFCct")


def short_flags(args: list[str], value_letters: frozenset[str] = frozenset()) -> str:
    """Letters of short-option clusters, stopping at a letter that takes a value."""
    letters: list[str] = []
    skip_next = False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if not arg.startswith("-") or arg.startswith("--"):
            continue
        for position, letter in enumerate(arg[1:], start=1):
            letters.append(letter)
            if letter in value_letters:
                skip_next = position == len(arg) - 1  # value is the next token
                break
    return "".join(letters)


def _is_no_verify(arg: str) -> bool:
    return len(arg) >= _MIN_NO_VERIFY_PREFIX and "--no-verify".startswith(arg)


def split_git(argv: list[str]) -> tuple[list[str], str, list[str]] | None:
    """(global `-c` configs, subcommand, args) for a git argv; None otherwise."""
    if not argv or posixpath.basename(argv[0]) != "git":
        return None
    configs: list[str] = []
    index = 1
    while index < len(argv) and argv[index].startswith("-"):
        option = argv[index]
        if option in _GIT_OPTS_WITH_VALUE and index + 1 < len(argv):
            if option == "-c":
                configs.append(argv[index + 1])
            index += 2
        else:
            index += 1
    if index >= len(argv):
        return None
    return configs, argv[index], argv[index + 1 :]


def _push_reason(args: list[str], current_branch: BranchLookup) -> str | None:
    """First matching push rule, checked in priority order."""
    options = set(args)
    targets = [a for a in args if not a.startswith("-")][1:]  # first positional is the remote
    flags = short_flags(args, _PUSH_VALUE_LETTERS)
    unsafe_force = [a for a in args if a.startswith("--force") and not a.startswith(_SAFE_FORCE)]
    implicit = not targets or any(t in _IMPLICIT_REFS for t in targets)
    checks: tuple[tuple[bool, str], ...] = (
        (any(_is_no_verify(a) for a in args), NO_VERIFY),
        (
            any(
                t.lstrip("+") == "main" or t.endswith((":main", "refs/heads/main")) for t in targets
            ),
            MAIN,
        ),
        (bool({"--all", "--mirror"} & options), MAIN),
        (bool(unsafe_force) or "f" in flags or any(t.startswith("+") for t in targets), FORCE),
        (
            bool({"--tags", "--follow-tags"} & options)
            or any(_TAG_REF.match(t.lstrip("+")) for t in targets),
            TAGS,
        ),
        (
            bool({"--delete", "--prune"} & options)
            or "d" in flags
            or any(t.startswith(":") for t in targets),
            DELETE,
        ),
    )
    for matched, reason in checks:
        if matched:
            return reason
    # Only now ask git which branch is checked out (costs a subprocess).
    return MAIN if implicit and current_branch() == "main" else None


def _commit_reason(args: list[str]) -> str | None:
    long_flags = [a for a in args if a.startswith("--")]
    if any(_is_no_verify(a) for a in long_flags) or "n" in short_flags(args, _COMMIT_VALUE_LETTERS):
        return NO_VERIFY
    return None


def _discards_work(sub: str, args: list[str]) -> bool:
    flags = short_flags(args)
    long_flags = set(args)
    checks = {
        "reset": "--hard" in long_flags,
        "clean": ("--force" in long_flags or "f" in flags)
        and not ("n" in flags or "--dry-run" in long_flags),
        "checkout": "--force" in long_flags or "f" in flags or "--" in args or "." in args,
        "restore": not ("--staged" in long_flags or "S" in flags)
        or "--worktree" in long_flags
        or "W" in flags,
        "stash": args[:1] == ["clear"],
        "branch": "D" in flags
        or (
            ("--delete" in long_flags or "d" in flags) and ("--force" in long_flags or "f" in flags)
        ),
        "update-ref": "-d" in args or "--delete" in long_flags,
    }
    return checks.get(sub, False)


def git_reason(argv: list[str], current_branch: BranchLookup) -> str | None:
    """Why this git argv is blocked, or None."""
    parsed = split_git(argv)
    if parsed is None:
        return None
    configs, sub, args = parsed
    if any(c.lower().startswith("core.hookspath") for c in configs):
        return NO_VERIFY
    if sub == "push":
        return _push_reason(args, current_branch)
    if sub == "commit":
        return _commit_reason(args)
    return DESTRUCTIVE if _discards_work(sub, args) else None
