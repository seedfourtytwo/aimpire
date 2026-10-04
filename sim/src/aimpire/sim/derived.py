"""Physical rates derived from the world constants (ADR-0020, W0).

Why this type lives in ``aimpire.sim``: systems consume these rates, and the
simulation package may not import ``aimpire.rules`` (it does no I/O). The rules
loader computes the values (``aimpire.rules.physics.derive_world``) and hands
the simulation this plain, frozen record, as it does with ``Calendar``.

Units: every rate is an integer multiplier in ppm of its Earth value, so
1_000_000 means "as on Earth" and 950_000 means 5 % less. A system scales its
own Earth base rate by it, for example ``base * walk_speed // PPM`` through
``aimpire.sim.fixed``. No floats are stored or hashed (ADR-0012).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DerivedWorld:
    """Rate multipliers in ppm of Earth, plus the laws used beyond their validated range.

    ``beyond_model`` names each law whose input constant lies outside the range
    where its source supports it, in law order. The value is still computed, so
    the Lab can explore, but a run that uses it is tagged ``beyond-model``.
    """

    walk_speed: int
    """Walking speed; scales with sqrt(gravity)."""
    carry_load: int
    """Load one person can carry; scales with 1/gravity."""
    walk_energy: int
    """Energy to walk a given distance; scales with gravity."""
    water_speed: int
    """River and flood flow speed; scales with sqrt(gravity)."""
    tree_height: int
    """Tallest possible tree; scales with gravity^(-1/3)."""
    fall_harm: int
    """Harm from a fall of a given height; scales with gravity."""
    throw_range: int
    """Range of a throw or spear at a given speed; scales with 1/gravity."""
    season_strength: int
    """Summer and winter contrast; scales with sin(tilt) / sin(23.44 degrees)."""
    plant_ceiling: int
    """Plant growth ceiling; min(sunlight, rain) (Liebig's law of the minimum)."""
    beyond_model: tuple[str, ...] = ()
