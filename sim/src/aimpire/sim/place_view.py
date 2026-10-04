"""Read-only typed views of place entities (ADR-0013 section 1; layout in ``places``).

Why a module of its own: every system reads places every tick (forage,
scout, the observation builder), so reading them is the hot path, while
``places`` builds the partition and measures travel. ``places`` re-exports
everything here, so callers import from ``aimpire.sim.places`` as before.

Tiles are checked in one numpy pass: a 64 by 64 map holds 4,096 tile pairs,
and checking them one by one dominated the run time of a game.
"""

from dataclasses import dataclass
from typing import Final

import numpy as np

from aimpire.sim.state import Entity, Value, WorldState

PLACE: Final = "place"

Tile = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Place:
    """Read-only typed view of one place entity."""

    entity_id: int
    place_id: str
    kind: str
    tiles: tuple[Tile, ...]
    centroid: Tile
    neighbours: tuple[str, ...]


def _int(value: Value, where: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{where} must be an int")
    return value


def _str(value: Value, where: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{where} must be a str")
    return value


def _list(value: Value, where: str) -> list[Value]:
    if not isinstance(value, list):
        raise TypeError(f"{where} must be a list")
    return value


def _pair(value: Value, where: str) -> Tile:
    items = _list(value, where)
    if len(items) != 2:
        raise TypeError(f"{where} must be a [row, col] pair")
    return _int(items[0], where), _int(items[1], where)


def _tiles(value: Value, where: str) -> tuple[Tile, ...]:
    """``[[row, col], ...]`` as tile tuples, checked in one numpy pass (it is read every tick)."""
    items = _list(value, where)
    if not items:
        return ()
    try:
        grid = np.asarray(items)
    except ValueError as exc:  # ragged nesting
        raise TypeError(f"{where} must be a list of [row, col] int pairs") from exc
    if grid.dtype != np.int64 or grid.ndim != 2 or grid.shape[1] != 2:
        raise TypeError(f"{where} must be a list of [row, col] int pairs")
    rows: list[int] = grid[:, 0].tolist()
    cols: list[int] = grid[:, 1].tolist()
    return tuple(zip(rows, cols, strict=True))


def _view(entity_id: int, entity: Entity, *, with_tiles: bool = True) -> Place:
    where = f"place entity {entity_id}"
    return Place(
        entity_id=entity_id,
        place_id=_str(entity.get("place_id"), f"{where}.place_id"),
        kind=_str(entity.get("place_kind"), f"{where}.place_kind"),
        tiles=_tiles(entity.get("tiles"), f"{where}.tiles") if with_tiles else (),
        centroid=_pair(entity.get("centroid"), f"{where}.centroid"),
        neighbours=tuple(
            _str(n, f"{where}.neighbours") for n in _list(entity.get("neighbours"), where)
        ),
    )


def places_by_id(state: WorldState, *, with_tiles: bool = True) -> dict[str, Place]:
    """Every place, keyed and ordered by place id.

    ``with_tiles=False`` leaves ``tiles`` empty: the travel functions need only
    centroids and neighbours, and skip reading thousands of tiles.
    """
    views = [
        _view(eid, state.entities[eid], with_tiles=with_tiles)
        for eid in sorted(state.entities)
        if state.entities[eid].get("kind") == PLACE
    ]
    return {p.place_id: p for p in sorted(views, key=lambda p: p.place_id)}


def tile_index(state: WorldState) -> dict[Tile, str]:
    """Map every tile to the id of the place containing it (built in place-id order)."""
    return {tile: pid for pid, place in places_by_id(state).items() for tile in place.tiles}


def place_of(state: WorldState, row: int, col: int) -> str:
    """Id of the place containing tile ``(row, col)``; ``KeyError`` if none does.

    Rebuilds the index on every call; callers looking up many tiles should
    build ``tile_index`` once.
    """
    index = tile_index(state)
    if (row, col) not in index:
        raise KeyError(f"no place contains tile ({row}, {col})")
    return index[(row, col)]
