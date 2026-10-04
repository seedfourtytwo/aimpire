"""World constants: read ``world.yaml`` and apply Lab overrides (ADR-0020, W0).

The constants are fundamental, not rates: systems never read them. The
physics laws (``aimpire.rules.physics``) turn them into ``DerivedWorld`` rates.

Units (ADR-0012, integers only):
    * ``gravity``, ``sunlight``, ``rain``: ppm of the Earth value (Earth = 1_000_000);
    * ``tilt``: milli-degrees (Earth = 23_440).

The loader refuses rather than coerces: a float, a bool, a quoted number, a
missing or unknown name is a ``RulesError``. Ranges beyond "the laws can be
computed" belong to the knob registry (``aimpire.lab.knobs``).
"""

from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Final

from aimpire.rules.errors import RulesError
from aimpire.rules.yaml_io import read_mapping


@dataclass(frozen=True, slots=True)
class WorldConstants:
    """The fundamental constants of one world, relative to Earth."""

    gravity: int
    """Surface gravity, ppm of Earth g. Must be positive (laws divide by it)."""
    sunlight: int
    """Mean surface sunlight, ppm of the Earth mean."""
    rain: int
    """Rainfall, ppm of the reference climate."""
    tilt: int
    """Axial tilt, milli-degrees, 0 to 90_000."""


EARTH: Final = WorldConstants(gravity=1_000_000, sunlight=1_000_000, rain=1_000_000, tilt=23_440)
"""The reference world. Every derived law is the identity here."""

NAMES: Final = tuple(f.name for f in fields(WorldConstants))
"""Constant names in declaration order."""

MAX_TILT: Final = 90_000
"""Tilt is a polar angle: 0 to 90 degrees, in milli-degrees."""


def _check(name: str, value: object) -> int:
    """Return ``value`` if it is a usable integer for constant ``name``; raise otherwise."""
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer, got {value!r}")
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    if name == "gravity" and value == 0:
        raise ValueError("gravity must be > 0: carry load and throw range divide by it")
    if name == "tilt" and value > MAX_TILT:
        raise ValueError(f"tilt must be <= {MAX_TILT} milli-degrees, got {value}")
    return value


def world_from_mapping(raw: Mapping[str, object]) -> WorldConstants:
    """Build and validate constants from a parsed mapping (exactly the known names)."""
    unknown = sorted(set(raw) - set(NAMES))
    missing = [name for name in NAMES if name not in raw]
    if unknown:
        raise ValueError(f"unknown world constants: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"missing world constants: {', '.join(missing)}")
    return WorldConstants(**{name: _check(name, raw[name]) for name in NAMES})


def apply_overrides(world: WorldConstants, overrides: Mapping[str, object]) -> WorldConstants:
    """Return ``world`` with constants replaced by ``overrides`` (keys are bare names)."""
    if not overrides:
        return world
    merged: dict[str, object] = {name: getattr(world, name) for name in NAMES}
    for name, value in overrides.items():
        if name not in merged:
            raise ValueError(f"unknown world constant {name!r}")
        merged[name] = value
    return replace(world, **{name: _check(name, merged[name]) for name in NAMES})


def load_world(rules_dir: Path, overrides: Mapping[str, object] | None = None) -> WorldConstants:
    """Read ``world.yaml`` from a rules version directory, then apply ``overrides``.

    ``overrides`` uses bare constant names (``{"gravity": 950_000}``); the Lab
    strips the ``world.`` prefix after checking each value against its knob.
    """
    path = Path(rules_dir).joinpath("world.yaml")
    try:
        return apply_overrides(world_from_mapping(read_mapping(path)), overrides or {})
    except RulesError:
        raise
    except ValueError as exc:
        raise RulesError(f"{path}: {exc}") from exc
