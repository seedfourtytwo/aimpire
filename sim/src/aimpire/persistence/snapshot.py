"""Full-state snapshots for checkpoints, format ``aimpire-snapshot-v1`` (ADR-0004).

A checkpoint stores everything ``aimpire.sim.hashing`` hashes, so a restored
state has the same ``state_hash`` as the one saved. That is what lets a
branch start from a checkpoint (ADR-0004) and lets a reviewer reload any
checkpoint of a run. Integers only: layers and carries are flattened
row-major lists of int64 values with their shape; entities are their
canonical JSON values keyed by integer id.
"""

from typing import Any, Final, cast

import numpy as np

from aimpire.sim.state import Entity, Int64Grid, WorldState, check_value

FORMAT: Final = "aimpire-snapshot-v1"


def _grid_value(grid: Int64Grid) -> dict[str, Any]:
    rows, cols = grid.shape
    return {"shape": [rows, cols], "data": [int(v) for v in grid.ravel().tolist()]}


def _grid(value: dict[str, Any]) -> Int64Grid:
    rows, cols = value["shape"]
    data = value["data"]
    if any(type(v) is not int for v in data):
        raise TypeError("snapshot grid data must be ints")
    return np.array(data, dtype=np.int64).reshape((rows, cols))


def to_value(state: WorldState) -> dict[str, Any]:
    """The state as JSON-ready data (ints, strings, lists, dicts). Validates first."""
    state.validate()
    return {
        "format": FORMAT,
        "run_seed": state.run_seed,
        "rules_version": state.rules_version,
        "rules_hash": state.rules_hash,
        "tick": state.tick,
        "next_id": state.next_id,
        "layers": {name: _grid_value(state.layers[name]) for name in sorted(state.layers)},
        "carries": {name: _grid_value(state.carries[name]) for name in sorted(state.carries)},
        "entities": [[i, state.entities[i]] for i in sorted(state.entities)],
    }


def from_value(value: dict[str, Any]) -> WorldState:
    """Rebuild a state from ``to_value`` output. Raises on any malformed part."""
    if value.get("format") != FORMAT:
        raise ValueError(f"not an {FORMAT} snapshot")
    state = WorldState(
        run_seed=value["run_seed"],
        rules_version=value["rules_version"],
        rules_hash=value["rules_hash"],
        tick=value["tick"],
        next_id=value["next_id"],
    )
    for name, grid in sorted(value["layers"].items()):
        state.layers[name] = _grid(grid)
    for name, grid in sorted(value["carries"].items()):
        state.carries[name] = _grid(grid)
    for entity_id, entity in value["entities"]:
        check_value(entity, f"entity {entity_id}")
        state.entities[entity_id] = cast(Entity, entity)
    state.validate()
    return state
