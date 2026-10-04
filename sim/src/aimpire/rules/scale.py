"""Read ``scale.yaml``, the map scale shared by every map (``aimpire.sim.scale``).

File reading lives here, outside ``aimpire.sim``; validation is
``MapScale.from_mapping``, so the record is checked the same way however it
is built.
"""

from pathlib import Path

from aimpire.rules.errors import RulesError
from aimpire.rules.yaml_io import read_mapping
from aimpire.sim.scale import MapScale


def load_map_scale(rules_dir: Path) -> MapScale:
    """Read and validate ``scale.yaml`` from a rules version directory. Raises ``RulesError``."""
    path = Path(rules_dir).joinpath("scale.yaml")
    try:
        return MapScale.from_mapping(read_mapping(path))
    except RulesError:
        raise
    except (TypeError, ValueError) as exc:
        raise RulesError(f"{path}: {exc}") from exc
