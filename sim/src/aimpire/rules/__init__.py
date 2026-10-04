"""Load versioned rules data from ``rules/<version>/`` (ADR-0011, ADR-0020).

File reading lives here, outside ``aimpire.sim``, which does no I/O. The
loader parses and validates; the simulation receives plain typed objects:
``Calendar`` from ``calendar.yaml`` and, through ``physics.derive_world``,
``DerivedWorld`` rates from the constants in ``world.yaml``.

No ``/`` operator anywhere in this package, not even to join paths
(``joinpath`` instead): the W0 acceptance test bans true division here, so a
float can never slip into a derived, hashed rate.
"""

from pathlib import Path

from aimpire.rules.digest import rules_hash
from aimpire.rules.errors import RulesError
from aimpire.rules.world import load_world
from aimpire.rules.yaml_io import read_mapping
from aimpire.sim.calendar import Calendar

__all__ = ["RulesError", "load_calendar", "load_world", "rules_hash"]


def load_calendar(rules_dir: Path) -> Calendar:
    """Read ``calendar.yaml`` from a rules version directory."""
    path = Path(rules_dir).joinpath("calendar.yaml")
    try:
        return Calendar.from_mapping(read_mapping(path))
    except RulesError:
        raise
    except ValueError as exc:
        raise RulesError(f"{path}: {exc}") from exc
