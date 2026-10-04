"""A minimal PNG encoder using only ``zlib`` and ``struct`` (F4a).

Why our own: a frame is a few hundred pixels of 8-bit RGB, and the spec for
that case is short. Writing it here avoids a Pillow dependency for one
function. Only what the frames need is supported: colour type 2 (RGB), bit
depth 8, no interlace, filter type 0 ("None") on every row.

The PNG bytes are not part of any pinned hash: zlib output may change between
library versions. Pin the array (``frames.frame_array``) instead.
"""

import struct
import zlib
from pathlib import Path
from typing import Final

import numpy as np
import numpy.typing as npt

SIGNATURE: Final = b"\x89PNG\r\n\x1a\n"
_BIT_DEPTH: Final = 8
_COLOUR_RGB: Final = 2


def _chunk(kind: bytes, body: bytes) -> bytes:
    """Length, type, body, then CRC-32 over type and body (PNG section 5.3)."""
    crc = zlib.crc32(kind + body) & 0xFFFFFFFF
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)


def encode_png(array: npt.NDArray[np.uint8]) -> bytes:
    """Encode a ``(rows, cols, 3)`` uint8 array as PNG bytes."""
    if array.dtype != np.uint8 or array.ndim != 3 or array.shape[2] != 3:
        raise ValueError("expected a (rows, cols, 3) uint8 array")
    rows, cols, _ = array.shape
    if rows < 1 or cols < 1:
        raise ValueError("an image needs at least one pixel")
    data = np.ascontiguousarray(array)
    # Each scanline starts with its filter-type byte; 0 means the raw bytes follow.
    raw = b"".join(b"\x00" + data[r].tobytes() for r in range(rows))
    header = struct.pack(">IIBBBBB", cols, rows, _BIT_DEPTH, _COLOUR_RGB, 0, 0, 0)
    return (
        SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )


def write_png(array: npt.NDArray[np.uint8], path: Path) -> None:
    """Encode ``array`` and write it to ``path``."""
    Path(path).write_bytes(encode_png(array))
