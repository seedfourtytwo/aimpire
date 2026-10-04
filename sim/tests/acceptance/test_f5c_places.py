"""F5c acceptance: named places partition the map (ADR-0013 section 1).

Written by the planning model before implementation (ADR-0016). Read-only.
Places are ordinary ``place`` entities, so they are hashed as ``entities:place``.
"""

import os
import subprocess
import sys

import numpy as np
import pytest

from aimpire.sim.hashing import diff_parts, state_hash
from aimpire.sim.places import grid_blocks, place_of, places_by_id, set_name, travel_ticks
from aimpire.sim.state import WorldState

pytestmark = pytest.mark.acceptance

BUILD = """
import numpy as np
from aimpire.sim.places import grid_blocks
from aimpire.sim.state import WorldState

def build(rows=5, cols=7, block_rows=2, block_cols=3):
    s = WorldState(run_seed=42, rules_version="v1", rules_hash="abc")
    s.add_layer("food", np.zeros((rows, cols), dtype=np.int64))
    grid_blocks(s, block_rows, block_cols)
    return s
"""

_ns: dict[str, object] = {}
exec(BUILD, _ns)  # the same builder runs here and in fresh interpreters
build = _ns["build"]  # type: ignore[assignment]


def _empty(rows: int, cols: int) -> WorldState:
    s = WorldState(run_seed=1, rules_version="v1", rules_hash="x")
    s.add_layer("food", np.zeros((rows, cols), dtype=np.int64))
    return s


def _hash_in_fresh_process(hashseed: str) -> str:
    code = BUILD + "\nfrom aimpire.sim.hashing import state_hash\nprint(state_hash(build()))\n"
    env = {**os.environ, "PYTHONHASHSEED": hashseed}
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, check=False
    )
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def test_partition_covers_every_tile_exactly_once() -> None:
    s = build()  # type: ignore[operator]
    seen: list[tuple[int, int]] = []
    for place in places_by_id(s).values():
        seen.extend((r, c) for r, c in place.tiles)
    assert sorted(seen) == [(r, c) for r in range(5) for c in range(7)]


def test_remainder_goes_to_last_block() -> None:
    """5 by 7 with 2 by 3 blocks: 2 by 2 places; the last row and column absorb leftovers."""
    s = build()  # type: ignore[operator]
    places = places_by_id(s)
    assert list(places) == ["PL01", "PL02", "PL03", "PL04"]
    sizes = [len(p.tiles) for p in places.values()]
    assert sizes == [2 * 3, 2 * 4, 3 * 3, 3 * 4]
    assert all(p.kind == "land" for p in places.values())


def test_ids_returned_and_entities_are_places() -> None:
    s = _empty(4, 4)
    ids = grid_blocks(s, 2, 2)
    assert ids == sorted(ids) and len(ids) == 4
    assert all(s.entities[i]["kind"] == "place" for i in ids)
    by_entity = {p.entity_id: pid for pid, p in places_by_id(s).items()}
    assert [by_entity[i] for i in ids] == ["PL01", "PL02", "PL03", "PL04"]


def test_place_ids_and_hash_stable_across_runs_and_processes() -> None:
    a, b = build(), build()  # type: ignore[operator]
    assert list(places_by_id(a)) == list(places_by_id(b))
    assert state_hash(a) == state_hash(b)
    assert _hash_in_fresh_process("1") == state_hash(a)
    assert _hash_in_fresh_process("98765") == state_hash(a)


def test_neighbours_symmetric_and_sorted() -> None:
    s = build(rows=9, cols=10, block_rows=3, block_cols=4)  # type: ignore[operator]
    places = places_by_id(s)
    for pid, place in places.items():
        assert list(place.neighbours) == sorted(place.neighbours)
        assert pid not in place.neighbours
        for other in place.neighbours:
            assert pid in places[other].neighbours
    # 3 block rows by 2 block columns: a corner touches two, a middle-row block three.
    assert list(places["PL01"].neighbours) == ["PL02", "PL03"]
    assert list(places["PL03"].neighbours) == ["PL01", "PL04", "PL05"]


def test_place_of_agrees_with_tiles() -> None:
    s = build()  # type: ignore[operator]
    for pid, place in places_by_id(s).items():
        for r, c in place.tiles:
            assert place_of(s, r, c) == pid
    with pytest.raises(KeyError):
        place_of(s, 5, 0)
    with pytest.raises(KeyError):
        place_of(s, -1, 0)


def test_centroids_are_integer_tiles_inside_the_place() -> None:
    s = _empty(4, 6)
    grid_blocks(s, 2, 2)
    centroids = {pid: tuple(p.centroid) for pid, p in places_by_id(s).items()}
    assert centroids == {
        "PL01": (0, 0), "PL02": (0, 2), "PL03": (0, 4),
        "PL04": (2, 0), "PL05": (2, 2), "PL06": (2, 4),
    }  # fmt: skip
    for p in places_by_id(s).values():
        assert all(type(v) is int for v in p.centroid)
        assert tuple(p.centroid) in {(r, c) for r, c in p.tiles}


def test_travel_ticks_on_known_map() -> None:
    s = _empty(4, 6)
    grid_blocks(s, 2, 2)
    assert travel_ticks(s, "PL01", "PL01") == 0
    assert travel_ticks(s, "PL01", "PL02") == 2
    assert travel_ticks(s, "PL01", "PL06") == 6
    assert travel_ticks(s, "PL03", "PL04") == 6
    with pytest.raises(KeyError):
        travel_ticks(s, "PL01", "PL99")


def test_travel_ticks_with_remainder_block() -> None:
    s = _empty(5, 5)
    grid_blocks(s, 2, 2)
    assert tuple(places_by_id(s)["PL04"].centroid) == (3, 3)
    assert travel_ticks(s, "PL01", "PL04") == 6
    assert travel_ticks(s, "PL02", "PL03") == 6


def test_travel_ticks_symmetric() -> None:
    s = build(rows=11, cols=13, block_rows=3, block_cols=4)  # type: ignore[operator]
    ids = list(places_by_id(s))
    for a in ids:
        for b in ids:
            assert travel_ticks(s, a, b) == travel_ticks(s, b, a)


def test_errors() -> None:
    no_layers = WorldState(run_seed=1, rules_version="v1", rules_hash="x")
    with pytest.raises(ValueError):
        grid_blocks(no_layers, 2, 2)
    with pytest.raises(ValueError):
        grid_blocks(_empty(4, 4), 5, 2)
    with pytest.raises(ValueError):
        grid_blocks(_empty(4, 4), 2, 5)
    with pytest.raises(ValueError):
        grid_blocks(_empty(4, 4), 0, 2)
    twice = _empty(4, 4)
    grid_blocks(twice, 2, 2)
    with pytest.raises(ValueError):
        grid_blocks(twice, 2, 2)


def test_names_start_empty_and_touch_only_place_entities() -> None:
    s = build()  # type: ignore[operator]
    assert all(p.name == "" for p in places_by_id(s).values())
    named = build()  # type: ignore[operator]
    set_name(named, "PL02", "Riverbend")
    assert places_by_id(named)["PL02"].name == "Riverbend"
    assert diff_parts(s, named) == ["entities:place"]
    assert travel_ticks(named, "PL01", "PL04") == travel_ticks(s, "PL01", "PL04")
    with pytest.raises(KeyError):
        set_name(named, "PL99", "Nowhere")
