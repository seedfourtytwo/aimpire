"""Authoritative world state: tile layers, their carries, and entities (ADR-0007, ADR-0012).

Why the restrictions: everything in here is hashed after every tick, and
recorded replay must reproduce those hashes exactly on any machine. So:

* tile layers and their carries are 2-D numpy ``int64`` arrays of one shape;
* entity fields are JSON-like values built only from ``int``, ``str``, ``bool``,
  ``None``, lists and string-keyed dicts. Floats are rejected on entry;
* entity ids come from a monotonic counter held in the state itself, never from
  ``id()`` or ``uuid``. Ids start at 1 and are never reused.

The state is a plain container. Systems change it; only the hash module reads
it as a whole.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import cast

import numpy as np
import numpy.typing as npt

Int64Grid = npt.NDArray[np.int64]
Value = int | str | bool | None | list["Value"] | dict[str, "Value"]
Entity = dict[str, Value]

_KIND = "kind"


def check_value(value: object, where: str = "value") -> None:
    """Raise ``TypeError`` unless ``value`` is hashable state data (no floats anywhere)."""
    if value is None or type(value) in (int, str, bool):
        return
    if isinstance(value, list):
        for i, item in enumerate(cast(list[object], value)):
            check_value(item, f"{where}[{i}]")
        return
    if isinstance(value, dict):
        for key, item in cast(dict[object, object], value).items():
            if type(key) is not str:
                raise TypeError(f"{where}: dict keys must be str, got {key!r}")
            check_value(item, f"{where}.{key}")
        return
    raise TypeError(f"{where}: {type(value).__name__} is not allowed in state (ints, str only)")


def _check_grid(name: str, grid: object) -> None:
    if not isinstance(grid, np.ndarray) or grid.dtype != np.int64 or grid.ndim != 2:  # pyright: ignore[reportUnknownMemberType]
        raise TypeError(f"layer {name!r} must be a 2-D numpy int64 array")


@dataclass(slots=True)
class WorldState:
    """Everything the simulation knows about one run at one tick."""

    run_seed: int
    rules_version: str
    rules_hash: str
    tick: int = 0
    next_id: int = 1
    layers: dict[str, Int64Grid] = field(default_factory=dict[str, Int64Grid])
    carries: dict[str, Int64Grid] = field(default_factory=dict[str, Int64Grid])
    entities: dict[int, Entity] = field(default_factory=dict[int, Entity])

    def allocate_id(self) -> int:
        """Return a fresh entity id and advance the counter. Ids are never reused."""
        new_id = self.next_id
        self.next_id += 1
        return new_id

    def add_entity(self, kind: str, fields: Mapping[str, Value]) -> int:
        """Validate and store a new entity; return its id."""
        if not kind or _KIND in fields:
            raise ValueError("an entity needs a non-empty kind, given separately from its fields")
        entity: Entity = {_KIND: kind, **fields}
        check_value(entity, f"entity of kind {kind}")
        new_id = self.allocate_id()
        self.entities[new_id] = entity
        return new_id

    def add_layer(self, name: str, grid: Int64Grid) -> None:
        """Add a tile layer and its zero carry layer (ADR-0012: one carry per rate-driven grid)."""
        _check_grid(name, grid)
        if self.layers:
            shape = next(iter(self.layers.values())).shape
            if grid.shape != shape:
                raise ValueError(f"layer {name!r} has shape {grid.shape}, expected {shape}")
        if name in self.layers:
            raise ValueError(f"layer {name!r} already exists")
        self.layers[name] = grid
        self.carries[name] = np.zeros_like(grid)

    def validate(self) -> None:
        """Check every invariant the hash relies on. Raises on the first problem."""
        for name, number in (("run_seed", self.run_seed), ("tick", self.tick)):
            if type(number) is not int or number < 0:
                raise TypeError(f"{name} must be a non-negative int")
        if type(self.next_id) is not int or self.next_id < 1:
            raise TypeError("next_id must be a positive int")
        if set(self.layers) != set(self.carries):
            raise ValueError("every layer needs exactly one carry layer")
        for name, grid in self.layers.items():
            _check_grid(name, grid)
            _check_grid(f"{name} carry", self.carries[name])
            if self.carries[name].shape != grid.shape:
                raise ValueError(f"carry for {name!r} has the wrong shape")
        for entity_id, entity in self.entities.items():
            if type(entity_id) is not int or not 1 <= entity_id < self.next_id:
                raise ValueError(f"entity id {entity_id!r} was not allocated by this state")
            check_value(entity, f"entity {entity_id}")
            if type(entity.get(_KIND)) is not str:
                raise ValueError(f"entity {entity_id} has no kind")
