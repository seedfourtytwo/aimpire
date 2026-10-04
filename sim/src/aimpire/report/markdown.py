"""Markdown pieces shared by every report: escaped cells and pipe tables.

Why escape: cells hold model text, place names and ids. A pipe or a newline
inside one would otherwise break the table it sits in.
"""

from collections.abc import Sequence


def cell(value: object) -> str:
    """A Markdown table cell: pipes escaped, newlines flattened."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def table(header: Sequence[str], rows: Sequence[Sequence[object]]) -> list[str]:
    """A pipe table as lines: header, separator, one line per row."""
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    return lines
