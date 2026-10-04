"""Split a Bash command string into per-command argv lists.

Layer: agent tooling (stdlib only). Used by `guard_bash.py` so rules match
real commands, not text: quoted strings stay single tokens, heredoc bodies
are dropped (they are data), and `;`, `&&`, `||`, `|` and unquoted newlines
separate commands.

Must never: execute or expand anything. This is a best-effort tokenizer for
guardrails, not a full shell parser; CI remains the real gate.
"""

from __future__ import annotations

import re
import shlex

_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_]\w*)\1")
_SEPARATOR = re.compile(r"^[;&|()]+$")
_ASSIGNMENT = re.compile(r"^[A-Za-z_]\w*=")
# Words that run the command after them (`sudo git push` is still `git push`).
_RUNNERS = frozenset({"sudo", "command", "exec", "time", "nohup", "xargs"})


def strip_heredocs(command: str) -> str:
    """Drop heredoc bodies, keeping the line that opens each heredoc."""
    kept: list[str] = []
    terminator: str | None = None
    for line in command.split("\n"):
        if terminator is not None:
            if line.strip() == terminator:
                terminator = None
            continue
        kept.append(line)
        match = _HEREDOC.search(line)
        if match and "<<<" not in line:
            terminator = match.group(2)
    return "\n".join(kept)


def _newlines_to_separators(command: str) -> str:
    """Replace unquoted newlines with `;` so each line is its own command."""
    out: list[str] = []
    quote: str | None = None
    escaped = False
    for char in command:
        if escaped:
            out.append(" " if char == "\n" else char)  # backslash-newline = continuation
            escaped = False
        elif char == "\\" and quote != "'":
            out.append(char)
            escaped = True
        elif quote:
            quote = None if char == quote else quote
            out.append(char)
        elif char in "'\"":
            quote = char
            out.append(char)
        else:
            out.append(" ; " if char == "\n" else char)
    return "".join(out)


def _tokens(text: str) -> list[str]:
    """Shell-like tokens; falls back to whitespace splitting on bad quoting."""
    try:
        lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|()")
        lexer.whitespace_split = True
        return list(lexer)
    except ValueError:
        return re.sub(r"([;&|]+)", r" \1 ", text).split()


def _effective_argv(argv: list[str]) -> list[str]:
    """Strip leading `VAR=value` assignments, `env [VAR=..]` and runner words."""
    index = 0
    while index < len(argv):
        word = argv[index]
        if _ASSIGNMENT.match(word) or word in _RUNNERS:
            index += 1
        elif word == "env" and index + 1 < len(argv):
            index += 1
            while index < len(argv) and (
                argv[index].startswith("-") or _ASSIGNMENT.match(argv[index])
            ):
                index += 1
            if index == len(argv):
                return ["env"]  # `env VAR=1` with no command still prints the environment
        else:
            break
    return argv[index:]


def segments(command: str) -> list[list[str]]:
    """Return one argv list per simple command in `command`."""
    text = _newlines_to_separators(strip_heredocs(command))
    result: list[list[str]] = []
    current: list[str] = []
    for token in [*_tokens(text), ";"]:
        if _SEPARATOR.match(token):
            argv = _effective_argv(current)
            if argv:
                result.append(argv)
            current = []
        else:
            current.append(token)
    return result
