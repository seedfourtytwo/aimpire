"""Map scale: metres per tile and metres walked per tick (``rules/v1/scale.yaml``).

Why it lives in the state: travel times are read in two places that only get
the state, the systems (``survey.walk_ticks``) and the observation builder
(``places.travel_ticks_within``). So worldgen stores the scale once, in a
single entity of kind ``"map"``, and every travel function reads it from
there. It is hashed with the rest of the world (``entities:map``).

Units (ADR-0012), integers only:
    ``tile``           side of one tile, metres;
    ``walk_per_tick``  distance walked in one tick at Earth gravity, metres.

A path of ``n`` tile steps is ``n * tile`` metres and takes

    ticks(n) = ceil(n * tile / walk_per_tick)

at Earth walking speed; ``walk_ticks`` divides further by the W0
``walk_speed``. Rounding up means any walk of one or more tiles takes at least
one tick, and since ceil is monotone a shorter path never takes longer.

A state without a ``map`` entity (test worlds, the plumbing ``stub`` world)
uses ``TILE_PER_TICK``: one tile per tick, so ticks equal tile steps, the
behaviour before the scale existed.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from aimpire.sim.fixed import PPM, ceil_div
from aimpire.sim.state import Value, WorldState

MAP: Final = "map"
_KEYS: Final = {"tile", "walk_per_tick"}


@dataclass(frozen=True, slots=True)
class MapScale:
    """How long a tile is and how far a person walks in a tick at Earth gravity, in metres."""

    tile: int
    walk_per_tick: int

    def __post_init__(self) -> None:
        for name in ("tile", "walk_per_tick"):
            value: object = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"map scale {name} must be a positive integer, got {value!r}")

    def ticks(self, tiles: int, walk_speed: int = PPM) -> int:
        """Ticks to walk ``tiles`` tile steps at ``walk_speed`` (ppm of Earth), rounded up."""
        if tiles < 0:
            raise ValueError(f"tiles must be >= 0, got {tiles}")
        if walk_speed < 1:
            raise ValueError(f"walk_speed must be >= 1 ppm, got {walk_speed}")
        return ceil_div(tiles * self.tile * PPM, self.walk_per_tick * walk_speed)

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> MapScale:
        """Build from parsed ``scale.yaml``: exactly ``tile`` and ``walk_per_tick``."""
        if set(data) != _KEYS:
            missing, extra = sorted(_KEYS - set(data)), sorted(set(data) - _KEYS)
            raise ValueError(f"map scale: missing {missing}, unknown {extra}")
        tile, walk = data["tile"], data["walk_per_tick"]
        if type(tile) is not int or type(walk) is not int:
            raise ValueError(f"map scale values must be integers, got {tile!r} and {walk!r}")
        return cls(tile=tile, walk_per_tick=walk)


TILE_PER_TICK: Final = MapScale(tile=1, walk_per_tick=1)
"""One tile per tick: the scale of a state that stores none."""


def set_map_scale(state: WorldState, scale: MapScale) -> int:
    """Store ``scale`` in ``state`` as its one ``map`` entity; return the entity id."""
    if any(e.get("kind") == MAP for e in state.entities.values()):
        raise ValueError("the state already has a map scale")
    fields: dict[str, Value] = {"tile": scale.tile, "walk_per_tick": scale.walk_per_tick}
    return state.add_entity(MAP, fields)


def map_scale(state: WorldState) -> MapScale:
    """The stored scale, or ``TILE_PER_TICK`` if the state has none."""
    for eid in sorted(state.entities):
        entity = state.entities[eid]
        if entity.get("kind") == MAP:
            tile, walk = entity.get("tile"), entity.get("walk_per_tick")
            if type(tile) is not int or type(walk) is not int:
                raise TypeError("map entity fields must be ints")
            return MapScale(tile=tile, walk_per_tick=walk)
    return TILE_PER_TICK
