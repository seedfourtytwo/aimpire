"""SQLite connections and the migration runner for run databases (ADR-0004).

* SQLite 3.51.3 or later is required, because of the WAL-reset corruption
  fix; ``connect`` checks the linked library and refuses older ones.
* Writers use WAL mode, ``foreign_keys=ON`` and ``synchronous=NORMAL``. One
  writer per run (the sim thread); readers open read-only.
* Migrations are plain numbered SQL files in ``migrations/`` applied in
  order. ``PRAGMA user_version`` records the last one applied, and the
  manifest repeats it as ``schema_version``.
"""

import re
import sqlite3
from importlib import resources
from pathlib import Path
from typing import Final

MIN_SQLITE: Final = (3, 51, 3)
_MIGRATION_NAME: Final = re.compile(r"(\d{4})_[a-z0-9_]+\.sql")


def check_sqlite_version(version: tuple[int, int, int] = sqlite3.sqlite_version_info) -> None:
    """Raise ``RuntimeError`` if the linked SQLite is older than ``MIN_SQLITE``."""
    if version < MIN_SQLITE:
        found = ".".join(map(str, version))
        need = ".".join(map(str, MIN_SQLITE))
        raise RuntimeError(f"SQLite {found} is too old; the run store needs {need} or later")


def connect(path: Path, *, read_only: bool) -> sqlite3.Connection:
    """Open a run database. A writer gets WAL mode; a reader can never write."""
    check_sqlite_version()
    if read_only:
        db = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    else:
        db = sqlite3.connect(path)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db


def migrations() -> list[tuple[int, str]]:
    """Every migration as ``(number, sql)``, in order. Numbers run 1, 2, 3 without gaps."""
    folder = resources.files("aimpire.persistence") / "migrations"
    found: list[tuple[int, str]] = []
    for entry in folder.iterdir():
        match = _MIGRATION_NAME.fullmatch(entry.name)
        if match:
            found.append((int(match.group(1)), entry.read_text(encoding="utf-8")))
    found.sort()
    if [n for n, _ in found] != list(range(1, len(found) + 1)):
        raise RuntimeError("migrations must be numbered 0001, 0002, ... without gaps")
    return found


def migrate(db: sqlite3.Connection) -> int:
    """Apply every migration newer than the database; return the schema version."""
    current = int(db.execute("PRAGMA user_version").fetchone()[0])
    latest = current
    for number, sql in migrations():
        if number <= current:
            continue
        db.executescript(f"BEGIN;\n{sql}\nPRAGMA user_version = {number};\nCOMMIT;")
        latest = number
    return latest
