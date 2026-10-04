"""Scaling laws: world constants in, rate multipliers out (ADR-0020, W0).

Why derive: independent rates would make "change gravity" mean nothing.
Here one constant moves many rates together, as real physics does, and the
trade-offs (slower walking, heavier hauls) appear without any rule naming
them. Reasoning and sources: ``docs/research/90-tinkering-lab-and-world-physics.md``.

Units: every law takes constants in ppm of Earth (``gravity``, ``sunlight``,
``rain``) or milli-degrees (``tilt``) and returns a multiplier in ppm of the
Earth rate. At Earth constants every law returns exactly ``PPM``.

Integers only (no floats even here; derived values are hashed): see
``aimpire.rules.intmath`` for the roots, the sine table and the rounding rule
(nearest, ties up; at most half a ppm off; monotonic).

Validated range: where the law's source supports it. Outside it the value is
still computed, but ``derive_world`` lists the law in ``beyond_model``.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from aimpire.rules.intmath import cbrt_ratio_nearest, div_nearest, sin_scaled, sqrt_nearest
from aimpire.rules.world import EARTH, WorldConstants
from aimpire.sim.derived import DerivedWorld
from aimpire.sim.fixed import PPM

_EARTH_SINE: Final = sin_scaled(EARTH.tilt)
"""The sine of Earth's tilt from the same table, so Earth's season law is exactly 1."""


def walk_speed(gravity: int) -> int:
    """Walking speed ∝ sqrt(g). Returns ``round(sqrt(g * PPM))`` ppm.

    Walking is an inverted pendulum; the gait changes at a fixed Froude number
    v**2 / (g L), which held near 0.45-0.56 from 1 g down to 0.4 g (Kram,
    Domingo and Ferris 1997, J. Exp. Biol. 200: 821-826).
    Units: ``gravity`` in ppm of Earth g. Validated: 0.4 to 2 g.
    """
    return sqrt_nearest(gravity * PPM)


def carry_load(gravity: int) -> int:
    """Carry load ∝ 1/g. Returns ``round(PPM**2 / g)`` ppm.

    Muscles give a fixed force and a load weighs m g, so the mass a person can
    carry falls as gravity rises. Units: ppm of Earth g. Validated: 0.3 to 3 g.
    """
    return div_nearest(PPM * PPM, gravity)


def walk_energy(gravity: int) -> int:
    """Energy to walk a distance ∝ g (a first approximation). Returns ``g`` ppm.

    Most of the cost of walking is supporting and moving body weight (Farley
    and McMahon 1992, J. Appl. Physiol. 73: 2709-2712). Measured cost falls
    *less* than in proportion, so this law is marked as a W0 simplification.
    Units: ppm of Earth g. Validated: 0.5 to 1.5 g.
    """
    return gravity


def water_speed(gravity: int) -> int:
    """River and flood speed ∝ sqrt(g). Returns ``round(sqrt(g * PPM))`` ppm.

    Chézy and Manning flow: v = C sqrt(R S) with C ∝ sqrt(g).
    Units: ppm of Earth g. Validated: any positive g.
    """
    return sqrt_nearest(gravity * PPM)


def tree_height(gravity: int) -> int:
    """Tallest tree ∝ g**(-1/3). Returns ``round(cbrt(PPM**4 / g))`` ppm.

    Greenhill (1881): a column buckles under its own weight above a height
    ∝ (E I / (rho g A))**(1/3); see also McMahon 1973 on tree proportions.
    Note PPM * (PPM / g)**(1/3) = cbrt(PPM**4 / g). Units: ppm of Earth g.
    Validated: any positive g.
    """
    return cbrt_ratio_nearest(PPM**4, gravity)


def fall_harm(gravity: int) -> int:
    """Harm from a fall of a given height ∝ g. Returns ``g`` ppm.

    The energy of a fall is m g h. Units: ppm of Earth g. Validated: any g.
    """
    return gravity


def throw_range(gravity: int) -> int:
    """Throw and spear range ∝ 1/g. Returns ``round(PPM**2 / g)`` ppm.

    Projectile range at a fixed launch speed and angle is v**2 / g.
    Units: ppm of Earth g. Validated: 0.3 to 3 g.
    """
    return div_nearest(PPM * PPM, gravity)


def season_strength(tilt: int) -> int:
    """Season strength ∝ sin(tilt) / sin(23.44 degrees). Returns ppm of Earth's contrast.

    The summer-winter insolation contrast grows with the sine of the axial
    tilt. ``sin`` comes from the integer table in ``intmath``; Earth's own
    sine is read from the same table, so Earth gives exactly ``PPM``.
    Units: ``tilt`` in milli-degrees. Validated: 0 to 45 degrees.
    """
    return div_nearest(sin_scaled(tilt) * PPM, _EARTH_SINE)


def plant_ceiling(sunlight: int, rain: int) -> int:
    """Plant growth ceiling = min(sunlight, rain), in ppm of Earth.

    Liebig's law of the minimum: growth is limited by the scarcest input.
    Units: both in ppm of Earth. Validated: any values.
    """
    return min(sunlight, rain)


@dataclass(frozen=True, slots=True)
class Law:
    """One derived rate: its name in ``DerivedWorld``, input constant and validated range."""

    name: str
    reads: tuple[str, ...]
    """The constants it reads, by name in ``WorldConstants``."""
    validated: tuple[int, int] | None
    """Inclusive range of the single input where the source holds; ``None`` means any."""
    compute: Callable[[WorldConstants], int]

    def beyond(self, world: WorldConstants) -> bool:
        """True if the input constant lies outside the validated range."""
        if self.validated is None:
            return False
        low, high = self.validated
        return not low <= getattr(world, self.reads[0]) <= high


LAWS: Final = (
    Law("walk_speed", ("gravity",), (400_000, 2_000_000), lambda w: walk_speed(w.gravity)),
    Law("carry_load", ("gravity",), (300_000, 3_000_000), lambda w: carry_load(w.gravity)),
    Law("walk_energy", ("gravity",), (500_000, 1_500_000), lambda w: walk_energy(w.gravity)),
    Law("water_speed", ("gravity",), None, lambda w: water_speed(w.gravity)),
    Law("tree_height", ("gravity",), None, lambda w: tree_height(w.gravity)),
    Law("fall_harm", ("gravity",), None, lambda w: fall_harm(w.gravity)),
    Law("throw_range", ("gravity",), (300_000, 3_000_000), lambda w: throw_range(w.gravity)),
    Law("season_strength", ("tilt",), (0, 45_000), lambda w: season_strength(w.tilt)),
    Law("plant_ceiling", ("sunlight", "rain"), None, lambda w: plant_ceiling(w.sunlight, w.rain)),
)
"""Every law, in ``DerivedWorld`` field order. ``beyond_model`` follows this order."""


def validated_range(constant: str) -> tuple[int, int] | None:
    """The range of ``constant`` where every law that reads it is validated.

    The intersection of the laws' ranges; ``None`` if no law limits it. The
    knob registry's validated ranges must equal this (a unit test checks).
    """
    ranges = [law.validated for law in LAWS if constant in law.reads and law.validated]
    if not ranges:
        return None
    return max(low for low, _ in ranges), min(high for _, high in ranges)


def derive_world(world: WorldConstants) -> DerivedWorld:
    """Apply every law to ``world``; name the laws used beyond their validated range."""
    rates = {law.name: law.compute(world) for law in LAWS}
    beyond = tuple(law.name for law in LAWS if law.beyond(world))
    return DerivedWorld(**rates, beyond_model=beyond)
