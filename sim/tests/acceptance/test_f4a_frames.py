"""F4a acceptance: dot frames as integer RGB arrays, and a stdlib PNG writer (ADR-0010).

Written by the planning model before implementation (ADR-0016). Read-only.
The frame hash is taken over the ARRAY bytes, never the PNG bytes: zlib output
may differ between library versions, the pixels may not. FRAME_HASH pins the
frame format (ramp, palette, dot drawing); changing it is a visible decision.
"""

import hashlib
import os
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import numpy as np
import pytest

from aimpire.report import frames
from aimpire.report.png import encode_png, write_png
from aimpire.sim.state import WorldState

pytestmark = pytest.mark.acceptance

FRAME_HASH = "c3f0c3af7ed8e5a3176d827a123714c82d8ca273e396aa4b6e4cffdcad0ec951"

BUILD = """
import numpy as np
from aimpire.sim.rng import Stream, draw, stream_key, uniform_int
from aimpire.sim.state import WorldState

def build():
    s = WorldState(run_seed=2026, rules_version="v1", rules_hash="test")
    key = stream_key(2026, 0, Stream.WORLDGEN)
    grid = np.array([uniform_int(draw(key, i), 10_001) for i in range(12 * 16)], dtype=np.int64)
    s.add_layer("food", grid.reshape(12, 16))
    for i in range(6):
        row, col = uniform_int(draw(key, 1000 + i, 1), 12), uniform_int(draw(key, 1000 + i, 2), 16)
        s.add_entity("person" if i % 2 else "animal", {"pos": [row, col]})
    s.add_entity("place", {"label": "no position: never drawn"})
    return s
"""

_ns: dict[str, object] = {}
exec(BUILD, _ns)  # the same builder runs here and in fresh interpreters
build = _ns["build"]  # type: ignore[assignment]

HASH_CODE = (
    BUILD
    + """
import hashlib
from aimpire.report.frames import frame_array
arr = frame_array(build(), "food", ("person", "animal"))
print(hashlib.blake2b(arr.tobytes(), digest_size=32).hexdigest())
"""
)


def _hash_in_fresh_process(hashseed: str) -> str:
    env = {**os.environ, "PYTHONHASHSEED": hashseed}
    out = subprocess.run(
        [sys.executable, "-c", HASH_CODE], capture_output=True, text=True, env=env, check=False
    )
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def test_frame_array_hash_stable() -> None:
    arr = frames.frame_array(build(), "food", ("person", "animal"))  # type: ignore[operator]
    assert arr.dtype == np.uint8
    assert arr.shape == (12, 16, 3)
    digest = hashlib.blake2b(arr.tobytes(), digest_size=32).hexdigest()
    assert digest == FRAME_HASH
    assert _hash_in_fresh_process("0") == FRAME_HASH
    assert _hash_in_fresh_process("12345") == FRAME_HASH


def test_frame_ramp_and_dots_by_hand() -> None:
    """Integer ramp: c = (low * (255 - level) + high * level) // 255, level = v * 255 // max."""
    s = WorldState(run_seed=1, rules_version="v1", rules_hash="test")
    s.add_layer("food", np.array([[0, 500, 1000]], dtype=np.int64))
    s.add_entity("person", {"pos": [0, 2]})
    s.add_entity("animal", {"pos": [0, 2]})  # not in entity_kinds: not drawn
    s.add_entity("person", {"pos": [5, 5]})  # off the grid: skipped, never an error
    arr = frames.frame_array(s, "food", ("person",), scale_max=1000)
    assert tuple(arr[0, 0]) == frames.RAMP_LOW
    assert tuple(arr[0, 1]) == (150, 185, 148)
    assert tuple(arr[0, 2]) == frames.PALETTE[0]
    assert frames.PALETTE[0] not in (frames.RAMP_LOW, frames.RAMP_HIGH)
    no_dots = frames.frame_array(s, "food", (), scale_max=1000)
    assert tuple(no_dots[0, 2]) == frames.RAMP_HIGH
    # Values above scale_max are clipped, so a fixed scale keeps frames comparable.
    s.layers["food"][0, 0] = 5000
    assert tuple(frames.frame_array(s, "food", (), scale_max=1000)[0, 0]) == frames.RAMP_HIGH


def _read_png(data: bytes) -> tuple[int, int, bytes]:
    """Minimal PNG reader for the test: returns width, height and the raw IDAT stream."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, width, height, ctype = 8, b"", 0, 0, b""
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        ctype = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        (crc,) = struct.unpack(">I", data[pos + 8 + length : pos + 12 + length])
        assert crc == zlib.crc32(ctype + body)
        if ctype == b"IHDR":
            width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", body)
            assert (depth, colour, interlace) == (8, 2, 0)  # 8-bit RGB, not interlaced
        elif ctype == b"IDAT":
            idat += body
        pos += 12 + length
    assert ctype == b"IEND"
    return width, height, zlib.decompress(idat)


def test_png_decodes(tmp_path: Path) -> None:
    arr = frames.frame_array(build(), "food", ("person", "animal"))  # type: ignore[operator]
    path = tmp_path / "frame.png"
    write_png(arr, path)
    data = path.read_bytes()
    assert data == encode_png(arr)
    width, height, raw = _read_png(data)
    assert (height, width) == arr.shape[:2]
    expected = b"".join(b"\x00" + arr[r].tobytes() for r in range(arr.shape[0]))
    assert raw == expected


def test_png_rejects_bad_arrays() -> None:
    with pytest.raises(ValueError):
        encode_png(np.zeros((2, 2), dtype=np.uint8))
    with pytest.raises(ValueError):
        encode_png(np.zeros((2, 2, 3), dtype=np.int64))  # type: ignore[arg-type]
