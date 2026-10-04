"""Property tests for aimpire.sim.places: any valid grid partition is exact and symmetric."""

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from aimpire.sim.places import grid_blocks, place_of, places_by_id, tile_index, travel_ticks
from aimpire.sim.state import WorldState


@st.composite
def maps(draw: st.DrawFn) -> tuple[int, int, int, int]:
    rows = draw(st.integers(min_value=1, max_value=12))
    cols = draw(st.integers(min_value=1, max_value=12))
    return (
        rows,
        cols,
        draw(st.integers(min_value=1, max_value=rows)),
        draw(st.integers(min_value=1, max_value=cols)),
    )


def _partition(rows: int, cols: int, block_rows: int, block_cols: int) -> WorldState:
    s = WorldState(run_seed=7, rules_version="v1", rules_hash="x")
    s.add_layer("food", np.zeros((rows, cols), dtype=np.int64))
    grid_blocks(s, block_rows, block_cols)
    return s


@settings(max_examples=60, deadline=None)
@given(maps())
def test_cover_exactly_once(spec: tuple[int, int, int, int]) -> None:
    rows, cols, block_rows, block_cols = spec
    s = _partition(*spec)
    places = places_by_id(s)
    assert len(places) == (rows // block_rows) * (cols // block_cols)
    tiles = [t for p in places.values() for t in p.tiles]
    assert sorted(tiles) == [(r, c) for r in range(rows) for c in range(cols)]
    index = tile_index(s)
    assert all(place_of(s, r, c) == index[(r, c)] for r, c in [(0, 0), (rows - 1, cols - 1)])
    for p in places.values():
        assert p.centroid in set(p.tiles)


@settings(max_examples=60, deadline=None)
@given(maps())
def test_neighbours_and_travel_symmetric(spec: tuple[int, int, int, int]) -> None:
    s = _partition(*spec)
    places = places_by_id(s)
    for pid, p in places.items():
        assert pid not in p.neighbours
        assert list(p.neighbours) == sorted(p.neighbours)
        for other in p.neighbours:
            assert pid in places[other].neighbours
    ids = list(places)
    for a in ids:
        assert travel_ticks(s, a, a) == 0
        for b in ids:
            ab = travel_ticks(s, a, b)
            assert ab == travel_ticks(s, b, a)
            ca, cb = places[a].centroid, places[b].centroid
            assert ab >= abs(ca[0] - cb[0]) + abs(ca[1] - cb[1])
