"""Milestone presets and the system registry the scheduler builds them from (ADR-0010, ADR-0015).

Why a registry function and not a constant: systems read rules values
(regrowth rates, later the ration and carry load), and the simulation never
loads files. So the caller loads ``M0Rules`` and the W0 ``DerivedWorld`` and
asks for the factories bound to them:

    registry = system_registry(rules, derived=resolved.derived)
    scheduler = Scheduler(PRESETS["m0"], registry, calendar, quantities=m0_quantities())

Preset ``m0`` (M0a): ``regrowth``. M0b appends its systems here; the preset
pins their order so earlier runs stay reproducible.

Conserved quantities for the scheduler's checked mode (F3): ``m0_quantities``.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from aimpire.sim.derived import DerivedWorld
from aimpire.sim.fixed import PPM
from aimpire.sim.ledger import Measure, layer_total
from aimpire.sim.scheduler import Preset, PresetError, System, SystemFactory, SystemSpec
from aimpire.sim.state import Value
from aimpire.sim.systems import regrowth
from aimpire.sim.world.m0 import FOOD
from aimpire.sim.world.m0_rules import M0Rules

EARTH_RATES: Final = DerivedWorld(
    walk_speed=PPM,
    carry_load=PPM,
    walk_energy=PPM,
    water_speed=PPM,
    tree_height=PPM,
    fall_harm=PPM,
    throw_range=PPM,
    season_strength=PPM,
    plant_ceiling=PPM,
)
"""W0 rates at Earth constants (every law is the identity there)."""

M0: Final = Preset("m0", (SystemSpec(regrowth.NAME),))
"""The petri dish: regrowth (M0a). M0b adds foraging, camp, scouting and hunger."""

PRESETS: Final[Mapping[str, Preset]] = MappingProxyType({M0.name: M0})
"""Every registered preset, by name."""


def _no_params(name: str, params: Mapping[str, Value]) -> None:
    if params:
        raise PresetError(f"system {name!r} takes no preset parameters, got {sorted(params)}")


def system_registry(
    rules: M0Rules, *, derived: DerivedWorld = EARTH_RATES
) -> dict[str, SystemFactory]:
    """Factories for every system the presets may name, bound to these rules.

    ``derived`` carries the W0 rates for systems that scale by them (M0b:
    carry load, walking energy). Regrowth needs none: W0 reaches it through
    the ``ceiling`` layer built at worldgen. Pass the run's own
    ``resolve_variant(...).derived`` so Lab overrides reach every system.
    """
    del derived  # read by the M0b systems; kept in the signature so callers pass it now

    def make_regrowth(params: Mapping[str, Value]) -> System:
        _no_params(regrowth.NAME, params)
        return regrowth.Regrowth(rate=rules.regrowth_rate, seed=rules.regrowth_seed)

    return {regrowth.NAME: make_regrowth}


def m0_quantities() -> dict[str, Measure]:
    """Conserved materials for checked mode: standing food (mu). M0b adds stores."""
    return {regrowth.MATERIAL: layer_total(FOOD)}
