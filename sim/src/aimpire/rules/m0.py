"""Read ``m0.yaml``, the M0 petri dish rules (backlog M0).

File reading lives here, outside ``aimpire.sim``. Validation of the values is
``M0Rules.from_mapping`` plus ``M0Rules.check_calendar`` (period-dependent
limits), so the record is checked the same way however it is built.
"""

from pathlib import Path

from aimpire.rules.errors import RulesError
from aimpire.rules.yaml_io import read_mapping
from aimpire.sim.calendar import Calendar
from aimpire.sim.world.m0_rules import M0Rules


def load_m0_rules(rules_dir: Path, calendar: Calendar) -> M0Rules:
    """Read and validate ``m0.yaml`` from a rules version directory.

    ``calendar`` (from ``load_calendar`` on the same directory) resolves the
    rate periods for the per-tick limits. Raises ``RulesError``.
    """
    path = Path(rules_dir).joinpath("m0.yaml")
    try:
        rules = M0Rules.from_mapping(read_mapping(path))
        rules.check_calendar(calendar)
    except RulesError:
        raise
    except (TypeError, ValueError) as exc:
        raise RulesError(f"{path}: {exc}") from exc
    return rules
