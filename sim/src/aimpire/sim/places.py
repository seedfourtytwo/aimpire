"""Named places: a partition of the map that minds talk about (ADR-0013 section 1).

Why: models handle raw tile grids badly, so minds never see coordinates. They
name a place (``"PL07"``) and rule code turns that into tiles, paths and work.
A place is an ordinary entity of kind ``"place"``, so it is part of the state
hash as ``entities:place`` and needs no special handling in ``hashing``.

Stored fields of a place entity (ints and strings only, ADR-0012):
    ``place_id``    ``"PL"`` plus a 1-based, zero-padded block number. It comes
                    from the block's position, never from the entity id, so a
                    map partitioned the same way always has the same ids. The
                    pad width is at least 2 and grows with the number of places,
                    so string order equals numeric order within one map.
    ``place_kind``  a neutral land-cover word; ``"land"`` on the flat petri dish.
                    (The entity key ``kind`` is already ``"place"``; the view
                    below exposes this field as ``Place.kind``.)
    ``tiles``       ``[[row, col], ...]`` in row-major order.
    ``centroid``    ``[row, col]``, the floor of the mean tile coordinate.
    ``neighbours``  sorted place ids that share at least one tile edge.

Names: a place entity has no name. A name is what one civilization calls a
place, so it lives in that civilization's own ``civ`` entity, under
``names[place_id]`` (``set_civ_name``). A shared field would let one
civilization's names reach another's observation from M2 on. Names are text
only: no rule reads them (ADR-0019).

Partition ``grid_blocks``: the map is cut into ``rows // block_rows`` by
``cols // block_cols`` rectangles. Leftover rows and columns are absorbed by the
last block row and the last block column, so no place is smaller than one full
block and the count is exactly predictable. For the 64 by 64 petri dish use
``PETRI_BLOCK`` (16 by 16, giving 16 places); 12 by 12 gives 25. Both are inside
the 12 to 30 target of ADR-0013.

Travel: ``travel_ticks`` is the shortest path between centroids over the
neighbour graph, each hop weighted by the Manhattan distance between the two
centroids: tile steps, at one tile per tick until movement rules set a speed.
With unit weights this would be breadth-first search; weighting keeps the
oversized remainder blocks honest. The shortest distance is unique, so the
result is symmetric whatever the tie-breaking (equal entries pop by place id).
``travel_ticks`` is the true world distance, for physics and execution.

What a mind is told is ``travel_ticks_within``: the same search restricted to
an allowed set of places (the civilization's known places plus its camp), so a
path length never reveals a place the civilization has not seen. When the
known places do not connect, ``lower_bound_ticks`` gives the Manhattan
distance between the two centroids. It reads the two endpoints only, and it
never exceeds the true distance: every hop costs the Manhattan distance between
its centroids, so by the triangle inequality any path costs at least that. On
``grid_blocks`` it equals the block distance times the block step.

Out of scope: per-seed coined place names for the unfamiliar-world arm
(ADR-0018 section 3) belong to prompt rendering and parsing, not to the state.
"""

import heapq
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from typing import Final

from aimpire.sim.state import Entity, Value, WorldState

PLACE: Final = "place"
CIV: Final = "civ"
LAND: Final = "land"
PETRI_BLOCK: Final = 16
_PREFIX: Final = "PL"
_MIN_WIDTH: Final = 2

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


def _view(entity_id: int, entity: Entity) -> Place:
    where = f"place entity {entity_id}"
    return Place(
        entity_id=entity_id,
        place_id=_str(entity.get("place_id"), f"{where}.place_id"),
        kind=_str(entity.get("place_kind"), f"{where}.place_kind"),
        tiles=tuple(_pair(t, f"{where}.tiles") for t in _list(entity.get("tiles"), where)),
        centroid=_pair(entity.get("centroid"), f"{where}.centroid"),
        neighbours=tuple(
            _str(n, f"{where}.neighbours") for n in _list(entity.get("neighbours"), where)
        ),
    )


def places_by_id(state: WorldState) -> dict[str, Place]:
    """Every place, keyed and ordered by place id."""
    views = [
        _view(eid, state.entities[eid])
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


def _spans(length: int, block: int) -> list[range]:
    """Cut ``range(length)`` into ``length // block`` spans; the last absorbs the rest."""
    count = length // block
    return [range(i * block, length if i == count - 1 else (i + 1) * block) for i in range(count)]


def _centroid(tiles: list[Tile]) -> Tile:
    n = len(tiles)
    return sum(r for r, _ in tiles) // n, sum(c for _, c in tiles) // n


def _neighbours(owner: dict[Tile, str]) -> dict[str, list[str]]:
    """Places sharing a tile edge, from tile ownership (works for any partition shape)."""
    links: dict[str, set[str]] = {pid: set() for pid in owner.values()}
    for (r, c), pid in owner.items():
        for other_tile in ((r + 1, c), (r, c + 1)):
            other = owner.get(other_tile)
            if other is not None and other != pid:
                links[pid].add(other)
                links[other].add(pid)
    return {pid: sorted(found) for pid, found in links.items()}


def grid_blocks(state: WorldState, block_rows: int, block_cols: int) -> list[int]:
    """Partition the map into rectangular places; return the new entity ids in place-id order.

    The map shape comes from the state's layers (all share one shape). Raises
    ``ValueError`` if there are no layers, a block size is below 1 or larger
    than the map, or the state already has places.
    """
    if not state.layers:
        raise ValueError("the state has no layers, so the map has no shape")
    if any(e.get("kind") == PLACE for e in state.entities.values()):
        raise ValueError("the state already has places")
    rows, cols = next(iter(state.layers.values())).shape
    for label, block, extent in (
        ("block_rows", block_rows, rows),
        ("block_cols", block_cols, cols),
    ):
        if type(block) is not int or not 1 <= block <= extent:
            raise ValueError(f"{label} must be an int from 1 to {extent}, got {block!r}")
    row_spans, col_spans = _spans(rows, block_rows), _spans(cols, block_cols)
    width = max(_MIN_WIDTH, len(str(len(row_spans) * len(col_spans))))
    blocks: dict[str, list[Tile]] = {}
    for i, rs in enumerate(row_spans):
        for j, cs in enumerate(col_spans):
            pid = f"{_PREFIX}{i * len(col_spans) + j + 1:0{width}d}"
            blocks[pid] = [(r, c) for r in rs for c in cs]
    links = _neighbours({tile: pid for pid, tiles in blocks.items() for tile in tiles})
    ids: list[int] = []
    for pid, tiles in blocks.items():
        cr, cc = _centroid(tiles)
        fields: dict[str, Value] = {
            "place_id": pid,
            "place_kind": LAND,
            "tiles": [[r, c] for r, c in tiles],
            "centroid": [cr, cc],
            "neighbours": list[Value](links[pid]),
        }
        ids.append(state.add_entity(PLACE, fields))
    return ids


def set_civ_name(state: WorldState, civ_id: str, place_id: str, name: str) -> None:
    """Record what ``civ_id`` calls ``place_id``, in that civ's own ``names`` map.

    Text only: no rule reads it. ``KeyError`` for an unknown place or civ.
    """
    if type(name) is not str:
        raise TypeError("a place name must be a str")
    if place_id not in places_by_id(state):
        raise KeyError(f"unknown place {place_id!r}")
    found = [
        e for e in state.entities.values() if e.get("kind") == CIV and e.get("civ_id") == civ_id
    ]
    if len(found) != 1:
        raise KeyError(f"expected one civ entity for {civ_id!r}, found {len(found)}")
    names = found[0].setdefault("names", {})
    if not isinstance(names, dict):
        raise TypeError(f"civ {civ_id}.names must be a mapping")
    names[place_id] = name


def _step(a: Tile, b: Tile) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _shortest(
    places: dict[str, Place], from_place: str, to_place: str, allowed: AbstractSet[str] | None
) -> int | None:
    """Dijkstra over the neighbour graph, entering only ``allowed`` places (all if None)."""
    best: dict[str, int] = {from_place: 0}
    frontier: list[tuple[int, str]] = [(0, from_place)]
    while frontier:
        dist, pid = heapq.heappop(frontier)
        if pid == to_place:
            return dist
        if dist > best[pid]:
            continue
        here = places[pid]
        for other in here.neighbours:
            if allowed is not None and other not in allowed:
                continue
            new = dist + _step(here.centroid, places[other].centroid)
            if other not in best or new < best[other]:
                best[other] = new
                heapq.heappush(frontier, (new, other))
    return None


def _endpoints(state: WorldState, *pids: str) -> dict[str, Place]:
    places = places_by_id(state)
    for pid in pids:
        if pid not in places:
            raise KeyError(f"unknown place {pid!r}")
    return places


def travel_ticks(state: WorldState, from_place: str, to_place: str) -> int:
    """True tile steps between two centroids along the neighbour graph (module docstring).

    ``KeyError`` for an unknown place; ``ValueError`` if the two are not connected.
    """
    found = _shortest(_endpoints(state, from_place, to_place), from_place, to_place, None)
    if found is None:
        raise ValueError(f"no path from {from_place} to {to_place}")
    return found


def travel_ticks_within(
    state: WorldState, from_place: str, to_place: str, allowed: AbstractSet[str]
) -> int | None:
    """Like ``travel_ticks``, but every place on the path must be in ``allowed``.

    ``None`` if no such path exists. ``KeyError`` for an unknown place;
    ``ValueError`` if an endpoint is not in ``allowed``.
    """
    places = _endpoints(state, from_place, to_place)
    for pid in (from_place, to_place):
        if pid not in allowed:
            raise ValueError(f"{pid} is not in the allowed places")
    return _shortest(places, from_place, to_place, allowed)


def lower_bound_ticks(state: WorldState, from_place: str, to_place: str) -> int:
    """Manhattan distance between the two centroids: never more than ``travel_ticks``."""
    places = _endpoints(state, from_place, to_place)
    return _step(places[from_place].centroid, places[to_place].centroid)
