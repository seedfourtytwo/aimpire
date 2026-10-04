"""Load versioned rules data from ``rules/<version>/`` (ADR-0011, ADR-0020).

File reading lives here, outside ``aimpire.sim``, which does no I/O. The
loader parses and validates; the simulation receives plain typed objects:
``Calendar`` from ``calendar.yaml`` and, through ``physics.derive_world``,
``DerivedWorld`` rates from the constants in ``world.yaml``, ``M0Rules``
from ``m0.yaml`` and ``MapScale`` from ``scale.yaml``.

``DEFAULT_RULES_DIR`` is the repository's current rules version, for the
commands and registered worlds that need one when none is given.

No ``/`` operator anywhere in this package, not even to join paths
(``joinpath`` instead): the W0 acceptance test bans true division here, so a
float can never slip into a derived, hashed rate.
"""

from pathlib import Path
from typing import Final

from aimpire.rules.digest import rules_hash
from aimpire.rules.errors import RulesError
from aimpire.rules.m0 import load_m0_rules
from aimpire.rules.scale import load_map_scale
from aimpire.rules.world import load_world
from aimpire.rules.yaml_io import read_mapping
from aimpire.sim.calendar import Calendar

__all__ = [
    "DEFAULT_RULES_DIR",
    "RulesError",
    "load_calendar",
    "load_m0_rules",
    "load_map_scale",
    "load_world",
    "rules_hash",
]

DEFAULT_RULES_DIR: Final = Path(__file__).resolve().parents[4].joinpath("rules", "v1")
"""``rules/v1`` of the checkout this package runs from (``sim/src/aimpire/rules`` -> repo)."""


def load_calendar(rules_dir: Path) -> Calendar:
    """Read ``calendar.yaml`` from a rules version directory."""
    path = Path(rules_dir).joinpath("calendar.yaml")
    try:
        return Calendar.from_mapping(read_mapping(path))
    except RulesError:
        raise
    except ValueError as exc:
        raise RulesError(f"{path}: {exc}") from exc
