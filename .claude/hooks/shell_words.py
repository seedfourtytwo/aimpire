"""Split a Bash command string into simple commands (env assignments + argv).

Layer: agent tooling (stdlib only). Used by `guard_bash.py` so rules match
real commands, not text:
- quoted strings stay single tokens; heredoc bodies are dropped (data);
- `;`, `&&`, `||`, `|`, `(`, `)` and unquoted newlines separate commands;
- `$(...)` and backtick substitutions are extracted as extra commands;
- wrappers and keywords (`timeout 30`, `nice -n 5`, `sudo`, `then`, `do`, `!`,
  `{`) are stripped so the real command is what rules see.

Must never: execute or expand anything. A best-effort tokenizer for
guardrails, not a full shell parser; CI remains the real gate.
"""

from __future__ import annotations

import re
import shlex
from typing import NamedTuple

_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_]\w*)\1")
_SUBSTITUTION = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")
_SEPARATOR = re.compile(r"^[;&|()]+$")
_ASSIGNMENT = re.compile(r"^[A-Za-z_]\w*=")
# Words dropped before the real command (no argument of their own).
_PREFIX_WORDS = frozenset(
    {"sudo", "command", "exec", "time", "nohup", "xargs", "do", "then", "else", "elif"}
    | {"if", "while", "until", "!", "{", "}", "stdbuf", "nice", "timeout", "env"}
)
_DURATION = re.compile(r"^\d+(\.\d+)?[smhd]?$")


class Command(NamedTuple):
    """One simple command: leading `VAR=value` assignments and the argv."""

    env: tuple[str, ...]
    argv: list[str]


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


def _skip_wrapper_args(word: str, argv: list[str], index: int) -> int:
    """Index after a wrapper's own options/arguments (`timeout 30`, `nice -n 5`)."""
    while index < len(argv) and (argv[index].startswith("-") or _ASSIGNMENT.match(argv[index])):
        takes_value = argv[index] in {"-n", "-s", "-k", "--signal", "--kill-after", "-u"}
        index += 2 if takes_value else 1
    if word == "timeout" and index < len(argv) and _DURATION.match(argv[index]):
        index += 1
    return index


def _split_command(words: list[str]) -> Command:
    """Separate leading assignments and wrapper words from the real argv."""
    env: list[str] = []
    index = 0
    while index < len(words):
        word = words[index]
        if _ASSIGNMENT.match(word):
            env.append(word)
            index += 1
        elif word in _PREFIX_WORDS:
            end = _skip_wrapper_args(word, words, index + 1)
            env.extend(w for w in words[index + 1 : end] if _ASSIGNMENT.match(w))
            if word == "env" and end >= len(words):
                return Command(tuple(env), ["env"])  # bare `env` prints the environment
            index = end
        else:
            break
    return Command(tuple(env), words[index:])


def commands(command: str) -> list[Command]:
    """Return every simple command in `command`, including substitutions."""
    text = strip_heredocs(command)
    inner = [a or b for a, b in _SUBSTITUTION.findall(text)]
    text = text.replace("`", " ; ") + "".join(f" ; {part}" for part in inner)
    result: list[Command] = []
    current: list[str] = []
    for token in [*_tokens(_newlines_to_separators(text)), ";"]:
        if _SEPARATOR.match(token):
            parsed = _split_command(current)
            if parsed.argv or parsed.env:
                result.append(parsed)
            current = []
        else:
            current.append(token)
    return result


def segments(command: str) -> list[list[str]]:
    """Argv lists only (convenience for callers that ignore assignments)."""
    return [c.argv for c in commands(command) if c.argv]
