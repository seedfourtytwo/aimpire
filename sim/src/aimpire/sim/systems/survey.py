"""Travel time at the world's walking speed, and dated snapshots of what people see (M0b).

Travel. ``places.travel_tiles`` is the true path length in tile steps along
the neighbour graph. The map scale (``aimpire.sim.scale``, ``rules/v1/scale.yaml``)
gives metres per tile and metres walked per tick at Earth gravity, and W0
gives ``walk_speed`` in ppm of Earth (ADR-0020: speed ∝ √g). A walk therefore
takes

    walk_ticks = ceil(tile_steps * tile * PPM / (walk_per_tick * walk_speed))

ticks: slower walkers need more ticks, faster ones fewer, and a walk of one
or more tiles never takes zero ticks. At Earth (``walk_speed == PPM``) it
equals ``places.travel_ticks``. This is the true travel time used by the
systems; what a mind is told is ``places.travel_ticks_within`` at the same
walking speed: the same days when the known places hold the true path, and
never a route through an unseen place (no leak).

Sight. People who stand at a place see every place whose centroid lies
within ``scout_sight`` tiles (Manhattan) of that place's centroid, the place
itself included (``rules/v1/m0.yaml``: 16 tiles reaches the four edge
neighbours on the 16-tile grid). What they see is written into the tribe's
``known`` map as ``{"seen_tick": tick, "seen": {"food": mu}}``: the total wild
food on the place's tiles at that tick. It is a dated snapshot. Nothing
updates it afterwards except another visit, so the observation never shows
live truth.
"""

from typing import Final

import numpy as np

from aimpire.sim.places import Place, places_by_id, travel_tiles
from aimpire.sim.scale import map_scale
from aimpire.sim.state import Entity, Value, WorldState
from aimpire.sim.systems.tribe import FOOD, sub_dict
from aimpire.sim.world.m0 import FOOD as FOOD_LAYER

_ROW: Final = 0
_COL: Final = 1


def walk_ticks(state: WorldState, from_place: str, to_place: str, walk_speed: int) -> int:
    """Ticks to walk between two places at ``walk_speed`` (ppm of Earth); see module docstring."""
    tiles = travel_tiles(state, from_place, to_place)
    return map_scale(state).ticks(tiles, walk_speed)


def place_food(state: WorldState, place: Place) -> int:
    """True wild food on the place's tiles, mu. For physics and snapshots only."""
    if not place.tiles:
        return 0
    rows = np.fromiter((t[_ROW] for t in place.tiles), dtype=np.int64, count=len(place.tiles))
    cols = np.fromiter((t[_COL] for t in place.tiles), dtype=np.int64, count=len(place.tiles))
    return int(state.layers[FOOD_LAYER][rows, cols].sum(dtype=np.int64))


def in_sight(places: dict[str, Place], center: str, sight: int) -> list[str]:
    """Place ids whose centroid is within ``sight`` tiles (Manhattan) of ``center``'s, sorted."""
    cr, cc = places[center].centroid
    return [
        pid
        for pid, p in places.items()
        if abs(p.centroid[_ROW] - cr) + abs(p.centroid[_COL] - cc) <= sight
    ]


def survey(state: WorldState, entity: Entity, center: str, sight: int) -> list[tuple[str, int]]:
    """Record a dated snapshot of every place in sight of ``center``; return ``(place, mu)``.

    Places seen for the first time become known: this is how a tribe discovers
    the map.
    """
    places = places_by_id(state)
    known = sub_dict(entity, "known")
    seen: list[tuple[str, int]] = []
    for pid in in_sight(places, center, sight):
        food = place_food(state, places[pid])
        snapshot: dict[str, Value] = {FOOD: food}
        known[pid] = {"seen_tick": state.tick, "seen": snapshot}
        seen.append((pid, food))
    return seen


def describe_seen(seen: list[tuple[str, int]]) -> str:
    """Evidence text for a snapshot, in whole food units: ``"PL03 food 120, PL07 food 88"``."""
    return ", ".join(f"{pid} food {mu // 1000}" for pid, mu in seen)
