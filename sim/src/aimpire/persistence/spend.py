"""The monthly spend ledger across runs (backlog F6 budget rules, ADR-0004).

Each run keeps its own spend in its ``decisions`` table (``charged_micro_usd``
with the calendar ``month`` it was booked to). The monthly cap covers every
run, and ADR-0004 keeps one database per run, so the monthly total is the
sum over every ``runs/<run_id>/run.db``, read with read-only connections.

Months are UTC calendar months, ``YYYY-MM``. Reading the clock is fine here:
this is bookkeeping outside the simulation, never world time.
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from aimpire.persistence.db import connect

DB_NAME: Final = "run.db"
_MONTH: Final = re.compile(r"\d{4}-(0[1-9]|1[0-2])")


def current_month() -> str:
    """This calendar month in UTC, ``YYYY-MM``: the period of the monthly cap."""
    return datetime.now(UTC).strftime("%Y-%m")


def check_month(month: str) -> str:
    """Return ``month`` if it is ``YYYY-MM``; raise ``ValueError`` otherwise."""
    if not _MONTH.fullmatch(month):
        raise ValueError(f"month must be YYYY-MM, got {month!r}")
    return month


def month_spent(runs_root: Path, month: str) -> int:
    """Micro-dollars charged in ``month`` by every run store under ``runs_root``."""
    check_month(month)
    total = 0
    for path in sorted(runs_root.glob(f"*/{DB_NAME}")):
        db = connect(path, read_only=True)
        try:
            query = "SELECT COALESCE(SUM(charged_micro_usd), 0) FROM decisions WHERE month = ?"
            total += int(db.execute(query, (month,)).fetchone()[0])
        finally:
            db.close()
    return total
