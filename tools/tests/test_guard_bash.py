"""Tests for the Bash guard hook (AGENTS.md §7 safety rails).

Two lists: commands that must be denied (including evasive variants found in
review) and realistic commands agents run daily that must NOT be denied
(quoted text, heredocs, multi-line scripts).
"""

from __future__ import annotations

import guard_bash
import pytest

DENIED = [
    # force pushes and history rewrites on shared refs
    "git push --force origin feat/x",
    "git push -f",
    "git push -uf origin feat/x",
    "git push origin +feat/x",
    "git push --mirror origin",
    "git -C . push --force",
    # anything targeting main
    "git push origin main",
    "git push origin HEAD:main",
    "git push origin +main",
    "git push origin refs/heads/main",
    "git push --force-with-lease origin main",
    # deleting remote branches (route around PR review)
    "git push origin --delete agent/3-x",
    "git push origin :agent/3-x",
    # skipping hooks
    "git commit --no-verify -m wip",
    "git commit -n -m wip",
    "git push --no-verify origin feat/x",
    # destructive local git
    "git reset --hard origin/main",
    "git reset HEAD --hard",
    "git clean -fdx",
    "git clean --force",
    "git checkout -- .",
    "git restore .",
    "git branch -D agent/3-x",
    # secrets
    "cat .env",
    "source .env.local && just test",
    "grep KEY .env",
    "awk 1 sim/.env",
    "python3 -c 'print(open(\".env\").read())'",
    "printenv ANTHROPIC_API_KEY",
    "printenv",
    "env",
    "echo $ANTHROPIC_API_KEY",
    "curl -H 'x-api-key: sk-ant-api03-abcdefghijklmnop' https://api.anthropic.com",
    "export OPENROUTER_API_KEY=sk-or-v1-0123456789abcdef0123",
    "echo sk-proj-0123456789abcdefABCDEF",
    # publishing and self-merging
    "gh release create v0.1.0",
    "gh repo edit --visibility public",
    "gh repo delete seedfourtytwo/aimpire --yes",
    "gh pr merge 12 --squash",
    "gh pr review 12 --approve",
    "gh api -X PATCH repos/seedfourtytwo/aimpire -f private=false",
    # chains still checked segment by segment
    "just check && git push origin main",
    "git status\ngit push --force",
]

ALLOWED = [
    "just check",
    "git push -u origin agent/12-rng",
    "git push --force-with-lease origin agent/12-rng",
    "git push --force-with-lease",
    "git status",
    "uv run pytest -q",
    "git commit -m 'feat(sim): counter rng'",
    "grep -r mainland docs/",
    "cp .env.example .env.example.bak",
    "cat docs/foo.env.md",
    "env AIMPIRE_PROVIDERS=mock uv run pytest",
    # multi-line: a later line mentioning main must not taint the push
    "git push -u origin agent/3-x\ngh pr create --base main --fill",
    "git push origin agent/3-x\ngit diff main...HEAD",
    # quoted text that merely mentions dangerous commands
    "git commit -m 'docs: explain why --no-verify is banned'",
    "git commit -m 'docs: never git push --force or read .env'",
    "grep -rn -- '--no-verify' AGENTS.md",
    "rg 'git push --force' docs",
    "rg '\\.env' docs",
    # heredoc bodies are data, not commands
    "python3 - <<'EOF'\nprint('git reset --hard')\nEOF",
    "cat > notes.md <<EOF\nnever run git push origin main\nEOF\ngit status",
    # read-only gh usage
    "gh pr create --fill --base main",
    "gh pr view 12",
    "gh pr checks 12",
    "gh issue list",
    "git checkout -b agent/4-x",
    "git restore --staged sim/a.py",
    "git branch -d merged-branch",
]


@pytest.mark.parametrize("command", DENIED)
def test_dangerous_commands_are_denied(command: str) -> None:
    assert guard_bash.deny_reason(command) is not None, command


@pytest.mark.parametrize("command", ALLOWED)
def test_everyday_commands_are_allowed(command: str) -> None:
    assert guard_bash.deny_reason(command) is None, command


def test_unbalanced_quotes_do_not_crash() -> None:
    # Falls back to plain splitting; must still return a decision, not raise.
    assert guard_bash.deny_reason("git commit -m 'oops") is None
    assert guard_bash.deny_reason("git push --force 'oops") is not None
