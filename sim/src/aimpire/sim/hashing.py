"""Canonical state hashing, format ``aimpire-state-v1`` (ADR-0007, amended by ADR-0012).

Why: recorded replay must reproduce the state hash at every checkpoint, on any
machine, so the bytes that are hashed must not depend on dict insertion order,
Python's hash randomisation, platform byte order or float formatting.

Layout: the state is split into named parts. Each part has its own BLAKE2b-256
digest (``subsystem_hashes``), so a divergence names the part that differs.
``state_hash`` is BLAKE2b-256 over the sorted ``(part, digest)`` pairs.

Parts:
    ``meta``            run seed, rules version and hash, tick, id counter
    ``layer:<name>``    shape and little-endian int64 bytes of a tile layer
    ``carry:<name>``    the same for its carry layer
    ``entities:<kind>`` canonical JSON of that kind's entities, sorted by id

ADR-0007 named ``<i4`` layer bytes; ADR-0012 made layers int64, so ``<i8`` is used.
"""

import hashlib
import json
from typing import Final

import numpy as np

from aimpire.sim.state import Int64Grid, Value, WorldState

FORMAT: Final = "aimpire-state-v1"
_DIGEST_SIZE: Final = 32


def _digest(data: bytes) -> bytes:
    return hashlib.blake2b(data, digest_size=_DIGEST_SIZE, person=FORMAT.encode()).digest()


def _canonical_json(value: Value) -> bytes:
    """Sorted keys, no whitespace, ASCII only. Floats never reach here (``check_value``)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _grid_bytes(grid: Int64Grid) -> bytes:
    rows, cols = grid.shape
    header = f"{rows}x{cols}:".encode()
    return header + np.ascontiguousarray(grid, dtype="<i8").tobytes()


def subsystem_hashes(state: WorldState) -> dict[str, str]:
    """Return ``{part: hex digest}`` for every part of the state. Validates first."""
    state.validate()
    meta: Value = {
        "format": FORMAT,
        "run_seed": state.run_seed,
        "rules_version": state.rules_version,
        "rules_hash": state.rules_hash,
        "tick": state.tick,
        "next_id": state.next_id,
    }
    parts: dict[str, bytes] = {"meta": _canonical_json(meta)}
    for name, grid in state.layers.items():
        parts[f"layer:{name}"] = _grid_bytes(grid)
        parts[f"carry:{name}"] = _grid_bytes(state.carries[name])
    by_kind: dict[str, list[Value]] = {}
    for entity_id in sorted(state.entities):
        entity = state.entities[entity_id]
        kind = str(entity["kind"])
        by_kind.setdefault(kind, []).append([entity_id, entity])
    for kind, rows in by_kind.items():
        parts[f"entities:{kind}"] = _canonical_json(rows)
    return {name: _digest(data).hex() for name, data in sorted(parts.items())}


def state_hash(state: WorldState) -> str:
    """BLAKE2b-256 hex digest of the whole state."""
    pairs = subsystem_hashes(state)
    return _digest(_canonical_json([[k, v] for k, v in sorted(pairs.items())])).hex()


def diff_parts(a: WorldState, b: WorldState) -> list[str]:
    """Names of the parts whose digests differ: where two runs diverged."""
    ha, hb = subsystem_hashes(a), subsystem_hashes(b)
    return sorted(k for k in ha.keys() | hb.keys() if ha.get(k) != hb.get(k))
