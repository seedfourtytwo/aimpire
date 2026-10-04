"""Dot frames: one tile layer plus entity dots as a small RGB array (F4a, ADR-0010).

Why arrays: an agent in a cloud session must be able to *see* a run, and
tests must be able to pin what it sees. So a frame is a ``uint8`` array of
shape ``(rows, cols, 3)``, one pixel per tile, built with integer arithmetic
only. Its bytes hash identically on every machine; the PNG made from it is
just a container (``aimpire.report.png``).

Drawing rules (changing any of them changes the pinned frame hash):

* the layer is clipped to ``[0, scale_max]`` and mapped to a level
  ``v * 255 // scale_max``; each channel is
  ``(RAMP_LOW * (255 - level) + RAMP_HIGH * level) // 255``, a ramp from pale
  grey (nothing) to green (plenty);
* entities whose kind is in ``entity_kinds`` and that have ``"pos": [row, col]``
  inside the grid become single pixels coloured ``PALETTE[i]``, where ``i`` is
  the kind's index in ``entity_kinds``. They are drawn in ascending id order,
  so on a shared tile the newest entity is on top. Others are skipped.
"""

from collections.abc import Sequence
from typing import Final

import numpy as np
import numpy.typing as npt

from aimpire.sim.state import Entity, WorldState

RGB = tuple[int, int, int]
RgbArray = npt.NDArray[np.uint8]

RAMP_LOW: Final[RGB] = (240, 240, 236)
RAMP_HIGH: Final[RGB] = (60, 130, 60)
# Dot colours chosen to stand out from the grey/green ramp and from each other.
PALETTE: Final[tuple[RGB, ...]] = (
    (200, 30, 30),  # red
    (30, 90, 200),  # blue
    (20, 20, 20),  # near black
    (230, 120, 0),  # orange
    (140, 60, 170),  # purple
    (0, 160, 170),  # teal
)


def entity_pos(entity: Entity) -> tuple[int, int] | None:
    """The entity's ``[row, col]`` as a tuple, or ``None`` if it has no valid position."""
    pos = entity.get("pos")
    if not isinstance(pos, list) or len(pos) != 2:
        return None
    row, col = pos
    if type(row) is not int or type(col) is not int:
        return None
    return row, col


def layer_rgb(grid: npt.NDArray[np.int64], scale_max: int) -> RgbArray:
    """Map an int64 layer onto the grey/green ramp. ``scale_max`` must be >= 1."""
    if scale_max < 1:
        raise ValueError(f"scale_max must be >= 1, got {scale_max}")
    level = np.clip(grid, 0, scale_max).astype(np.int64) * 255 // scale_max
    low, high = np.array(RAMP_LOW, dtype=np.int64), np.array(RAMP_HIGH, dtype=np.int64)
    rgb = (low * (255 - level[..., None]) + high * level[..., None]) // 255
    return np.ascontiguousarray(rgb, dtype=np.uint8)


def default_scale(grid: npt.NDArray[np.int64]) -> int:
    """The layer's own maximum, at least 1: used when no fixed scale is given."""
    return max(int(grid.max()) if grid.size else 0, 1)


def frame_array(
    state: WorldState,
    layer: str,
    entity_kinds: Sequence[str],
    scale_max: int | None = None,
) -> RgbArray:
    """Return the ``(rows, cols, 3)`` uint8 frame for ``state``.

    ``scale_max`` fixes the value that maps to full green; pass the same value
    for every frame of a run so frames are comparable. By default it is the
    layer's own maximum (at least 1).
    """
    if len(entity_kinds) > len(PALETTE):
        raise ValueError(f"at most {len(PALETTE)} entity kinds can be coloured")
    if len(set(entity_kinds)) != len(entity_kinds):
        raise ValueError("entity_kinds must not repeat")
    grid = state.layers[layer]
    frame = layer_rgb(grid, default_scale(grid) if scale_max is None else scale_max)
    colour = {kind: PALETTE[i] for i, kind in enumerate(entity_kinds)}
    rows, cols = grid.shape
    for entity_id in sorted(state.entities):
        entity = state.entities[entity_id]
        kind = entity.get("kind")
        if not isinstance(kind, str) or kind not in colour:
            continue
        pos = entity_pos(entity)
        if pos is None or not (0 <= pos[0] < rows and 0 <= pos[1] < cols):
            continue
        frame[pos[0], pos[1]] = colour[kind]
    return frame


def upscale(frame: RgbArray, factor: int) -> RgbArray:
    """Nearest-neighbour enlargement by an integer ``factor``: tiles become squares."""
    if factor < 1:
        raise ValueError(f"factor must be >= 1, got {factor}")
    return np.ascontiguousarray(np.repeat(np.repeat(frame, factor, axis=0), factor, axis=1))
