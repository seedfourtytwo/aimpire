"""Worldgen for the M0 petri dish: fertility, food ceiling, food and places (backlog M0a).

Pure: takes an already-loaded ``M0Rules`` and ``DerivedWorld`` and returns a
fresh ``WorldState``. No I/O; the only randomness is the WORLDGEN stream at
tick 0 (ADR-0012), so a seed always makes the same world.

Layers (2-D int64, ``rules.rows`` by ``rules.cols``; each has a carry layer):
    ``fertility``  ppm, smooth value noise in ``[fertility_min, fertility_max]``.
    ``ceiling``    K, the food ceiling of each tile, in milli-units:
                   ``floor(food_ceiling * plant_ceiling * fertility / PPM**2)``.
                   ``plant_ceiling`` is W0's derived rate (ppm of Earth), so
                   sunlight and rain reach K through W0 and gravity does not
                   reach it at all. One floor, at the end, so the rounding
                   error is under 1 mu per tile.
    ``food``       F, standing wild food in milli-units, starting at
                   ``floor(K * initial_food / PPM)``. Regrowth changes it.

Places: ``grid_blocks`` with ``rules.place_block`` tiles a side.
"""

from typing import Final

import numpy as np

from aimpire.sim.derived import DerivedWorld
from aimpire.sim.fixed import PPM, Int64Array
from aimpire.sim.places import grid_blocks
from aimpire.sim.rng import SITES, stream_key
from aimpire.sim.state import WorldState
from aimpire.sim.world.m0_rules import M0Rules
from aimpire.sim.world.noise import value_noise

FERTILITY: Final = "fertility"
CEILING: Final = "ceiling"
FOOD: Final = "food"

_FERTILITY_STREAM, _FERTILITY_N = SITES["m0_fertility"]
_INT64_LIMIT: Final = 2**63
_WORLDGEN_TICK: Final = 0


def fertility_map(run_seed: int, rules: M0Rules) -> Int64Array:
    """The fertility layer (ppm) of the world made from ``run_seed``."""
    key = stream_key(run_seed, _WORLDGEN_TICK, _FERTILITY_STREAM)
    return value_noise(
        key,
        _FERTILITY_N,
        (rules.rows, rules.cols),
        rules.fertility_cell,
        (rules.fertility_min, rules.fertility_max),
    )


def tile_ceiling(rules: M0Rules, derived: DerivedWorld, fertility: Int64Array) -> Int64Array:
    """K per tile in milli-units: ``floor(food_ceiling * plant_ceiling * fertility / PPM**2)``.

    Raises ``OverflowError`` if the product could exceed int64 (a very large
    sunlight and rain override together with a large base ceiling).
    """
    scale = rules.food_ceiling * derived.plant_ceiling
    top = int(fertility.max()) if fertility.size else 0
    if scale * top >= _INT64_LIMIT:
        raise OverflowError("food_ceiling * plant_ceiling * fertility would exceed int64")
    # Floor of a product of two ppm scales, not a rate over time.
    return np.floor_divide(fertility * np.int64(scale), np.int64(PPM * PPM)).astype(np.int64)


def build_m0_world(
    run_seed: int,
    rules: M0Rules,
    derived: DerivedWorld,
    *,
    rules_version: str,
    rules_hash: str,
) -> WorldState:
    """Make the tick-0 petri dish: fertility, ceiling and food layers, then places.

    ``rules_hash`` should come from ``aimpire.lab.variant.resolve_variant``
    (rules files plus world overrides), the same call that gives ``derived``.
    """
    state = WorldState(run_seed=run_seed, rules_version=rules_version, rules_hash=rules_hash)
    fertility = fertility_map(run_seed, rules)
    ceiling = tile_ceiling(rules, derived, fertility)
    # Floor of a ppm share of the ceiling; at most K because initial_food <= PPM.
    food = np.floor_divide(ceiling * np.int64(rules.initial_food), np.int64(PPM))
    state.add_layer(FERTILITY, fertility)
    state.add_layer(CEILING, ceiling)
    state.add_layer(FOOD, food.astype(np.int64))
    grid_blocks(state, rules.place_block, rules.place_block)
    return state
