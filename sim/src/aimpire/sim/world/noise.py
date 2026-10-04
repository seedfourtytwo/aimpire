"""Integer value noise for worldgen (backlog M0a).

Why value noise: fertility should vary smoothly across the map, with rich and
poor regions, and come from the run seed alone. Value noise is the simplest
field with that shape: random values on a coarse lattice, interpolated
between lattice points. It needs one counter draw per lattice point and no
floats.

Method:
    * lattice points every ``cell`` tiles, covering the map:
      ``ceil(rows / cell) + 1`` by ``ceil(cols / cell) + 1`` points;
    * point ``(i, j)`` has id ``i * lattice_cols + j`` and value
      ``low + draw(key, id, n) mod (high - low + 1)``, uniform in
      ``[low, high]`` (modulo bias below 2**-40 for ppm spans);
    * tile ``(row, col)`` takes the bilinear mean of its cell's four corners,
      with integer weights ``(cell - dr)(cell - dc)`` and so on, summing to
      ``cell**2``. The mean is floored, so every tile is in ``[low, high]``.

The result depends only on ``(key, n, shape, cell, bounds)``: no draw
order, no hidden state (ADR-0012).
"""

from typing import Final

import numpy as np

from aimpire.sim.fixed import Int64Array
from aimpire.sim.rng import draw_array

_INT64_LIMIT: Final = 2**63


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def value_noise(
    key: int, n: int, shape: tuple[int, int], cell: int, bounds: tuple[int, int]
) -> Int64Array:
    """Return a ``shape`` int64 grid of smooth noise in ``bounds = (low, high)``, inclusive.

    ``key`` is a stream key (``rng.stream_key``) and ``n`` the draw index of
    the calling site (``rng.SITES``). ``cell`` is the lattice spacing in tiles.
    Raises ``ValueError`` for an empty shape, ``cell < 1`` or ``low > high``,
    and ``OverflowError`` if the weighted sum could exceed int64.
    """
    rows, cols = shape
    low, high = bounds
    if rows < 1 or cols < 1:
        raise ValueError(f"shape must be positive, got {shape}")
    if cell < 1:
        raise ValueError(f"cell must be >= 1, got {cell}")
    if not 0 <= low <= high:
        raise ValueError(f"need 0 <= low <= high, got {low}, {high}")
    if cell * cell * high >= _INT64_LIMIT:
        raise OverflowError("cell**2 * high would exceed int64")
    lat_rows, lat_cols = _ceil_div(rows, cell) + 1, _ceil_div(cols, cell) + 1
    ids = np.arange(lat_rows * lat_cols, dtype=np.uint64)
    span = np.uint64(high - low + 1)
    lattice = (draw_array(key, ids, n) % span).astype(np.int64) + np.int64(low)
    lattice = lattice.reshape(lat_rows, lat_cols)
    # Integer tile-to-lattice indexing: which cell a tile is in, and where.
    i0, dr = np.divmod(np.arange(rows, dtype=np.int64), np.int64(cell))
    j0, dc = np.divmod(np.arange(cols, dtype=np.int64), np.int64(cell))
    wr0, wr1 = (cell - dr)[:, None], dr[:, None]
    wc0, wc1 = (cell - dc)[None, :], dc[None, :]
    a = lattice[i0][:, j0]
    b = lattice[i0 + 1][:, j0]
    c = lattice[i0][:, j0 + 1]
    d = lattice[i0 + 1][:, j0 + 1]
    total = a * wr0 * wc0 + b * wr1 * wc0 + c * wr0 * wc1 + d * wr1 * wc1
    # Floor of a weighted mean (weights sum to cell**2), not a rate.
    return np.floor_divide(total, np.int64(cell * cell)).astype(np.int64)
