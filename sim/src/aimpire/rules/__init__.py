"""Load versioned rules data from ``rules/<version>/`` (ADR-0011).

File reading lives here, outside ``aimpire.sim``, which does no I/O. The
loader parses and validates; the simulation receives plain typed objects.
"""

from pathlib import Path

import yaml

from aimpire.sim.calendar import Calendar


class RulesError(ValueError):
    """A rules file is missing, unreadable or invalid."""


def _read_mapping(path: Path) -> dict[str, object]:
    try:
        data: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RulesError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RulesError(f"{path} must hold a mapping")
    return {str(k): v for k, v in data.items()}  # pyright: ignore[reportUnknownVariableType]


def load_calendar(rules_dir: Path) -> Calendar:
    """Read ``calendar.yaml`` from a rules version directory."""
    path = Path(rules_dir) / "calendar.yaml"
    try:
        return Calendar.from_mapping(_read_mapping(path))
    except RulesError:
        raise
    except ValueError as exc:
        raise RulesError(f"{path}: {exc}") from exc
