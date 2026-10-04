"""Milestone presets and the system registry the scheduler builds them from (ADR-0010, ADR-0015).

Why a registry function and not a constant: systems read rules values
(regrowth rates, the ration and carry load), and the simulation never
loads files. So the caller loads ``M0Rules`` and the W0 ``DerivedWorld`` and
asks for the factories bound to them:

    registry = system_registry(rules, derived=resolved.derived)
    scheduler = Scheduler(PRESETS["m0"], registry, calendar, quantities=m0_quantities())

Preset ``m0``, in this order (M0a regrowth, M0b the tribe):

1. ``regrowth``: wild food grows first, so the day's foragers find today's food;
2. ``camp``: moves, trip departures, and today's split of the free workers.
   It runs before the work systems so they all see one picture of who is
   where (a returning trip is free from the next tick, a finished move from
   this one);
3. ``forage``: standing foragers and FORAGE trips put food into the stores;
4. ``scout``: standing scouts and SCOUT trips take dated snapshots;
5. ``hunger``: people eat what is in the stores after the day's work, the
   rest spoils, and a shortfall can kill.

The preset pins this order so runs stay reproducible.

Conserved quantities for the scheduler's checked mode (F3): ``m0_quantities``.
"""

from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Final

from aimpire.sim.derived import DerivedWorld
from aimpire.sim.fixed import PPM
from aimpire.sim.ledger import Measure, entity_field_total, layer_total
from aimpire.sim.scheduler import Preset, PresetError, System, SystemFactory, SystemSpec
from aimpire.sim.state import Value
from aimpire.sim.systems import camp, forage, hunger, regrowth, scout
from aimpire.sim.systems.tribe import CIV, STORES
from aimpire.sim.systems.tribe import FOOD as STORES_FOOD
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

M0: Final = Preset(
    "m0",
    (
        SystemSpec(regrowth.NAME),
        SystemSpec(camp.NAME),
        SystemSpec(forage.NAME),
        SystemSpec(scout.NAME),
        SystemSpec(hunger.NAME),
    ),
)
"""The petri dish: regrowth (M0a), then the tribe (M0b) in the order above."""

PRESETS: Final[Mapping[str, Preset]] = MappingProxyType({M0.name: M0})
"""Every registered preset, by name."""


def _factory(name: str, build: Callable[[], System]) -> SystemFactory:
    """A factory that refuses preset parameters (no M0 system takes any)."""

    def make(params: Mapping[str, Value]) -> System:
        if params:
            raise PresetError(f"system {name!r} takes no preset parameters, got {sorted(params)}")
        return build()

    return make


def system_registry(
    rules: M0Rules, *, derived: DerivedWorld = EARTH_RATES
) -> dict[str, SystemFactory]:
    """Factories for every system the presets may name, bound to these rules.

    ``derived`` carries the W0 rates for systems that scale by them: walking
    speed (travel ticks), carry load and walking energy. Regrowth needs none:
    W0 reaches it through the ``ceiling`` layer built at worldgen. Pass the
    run's own ``resolve_variant(...).derived`` so Lab overrides reach every
    system.
    """
    builders: dict[str, Callable[[], System]] = {
        regrowth.NAME: lambda: regrowth.Regrowth(
            rate=rules.regrowth_rate, seed=rules.regrowth_seed
        ),
        camp.NAME: lambda: camp.Camp(
            walk_energy=rules.walk_energy,
            walk_speed=derived.walk_speed,
            walk_energy_scale=derived.walk_energy,
            sight=rules.scout_sight,
        ),
        forage.NAME: lambda: forage.Forage(
            carry_per_trip=rules.carry_per_trip,
            walk_energy=rules.walk_energy,
            carry_load=derived.carry_load,
            walk_speed=derived.walk_speed,
            walk_energy_scale=derived.walk_energy,
        ),
        scout.NAME: lambda: scout.Scout(
            walk_energy=rules.walk_energy,
            walk_speed=derived.walk_speed,
            walk_energy_scale=derived.walk_energy,
            sight=rules.scout_sight,
        ),
        hunger.NAME: lambda: hunger.Hunger(
            food_need=rules.food_need,
            store_spoilage=rules.store_spoilage,
            starvation_death=rules.starvation_death,
        ),
    }
    return {name: _factory(name, build) for name, build in builders.items()}


def m0_quantities() -> dict[str, Measure]:
    """Conserved materials for checked mode, both in mu.

    ``food`` is the standing wild food (the tile layer); ``stores`` is the food
    in every tribe's stores. Together they cover the whole food cycle:
    ``REGROWTH`` adds to food, ``HARVEST`` moves food into stores, and
    ``CONSUME`` and ``SPOIL`` take from stores.
    """
    return {
        regrowth.MATERIAL: layer_total(FOOD),
        STORES: entity_field_total(CIV, ("stores", STORES_FOOD)),
    }
