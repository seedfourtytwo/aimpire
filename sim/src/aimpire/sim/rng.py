"""Counter-based random draws, version ``aimpire-draw-v1`` (ADR-0012 section B).

Why counter-based: every draw is a pure function of where it is used
``(run seed, tick, stream, entity, n)``. There is no hidden generator state to
checkpoint, the order in which code asks for numbers never matters, and adding
a system or an entity never shifts anyone else's numbers. Recorded replay
therefore reproduces every state hash.

Two stages:
    1. ``stream_key`` hashes ``(run_seed, tick, stream)`` with BLAKE2b. This
       gives cryptographic separation between seeds, ticks and streams, once
       per stream per tick (about a microsecond).
    2. ``draw`` mixes the key with an entity id and a draw index ``n`` using a
       splitmix64 finaliser (about 10 ns per entity in ``draw_array``).

Changing anything here changes every stored run. It needs a new ADR, a new
version string and regenerated golden fixtures.
"""

import hashlib
import struct
from collections.abc import Iterable
from enum import IntEnum
from typing import Final

import numpy as np
import numpy.typing as npt

VERSION: Final = "aimpire-draw-v1"

U64_MAX: Final = 2**64 - 1
_GAMMA: Final = 0x9E3779B97F4A7C15
_C1: Final = 0xBF58476D1CE4E5B9
_C2: Final = 0x94D049BB133111EB
_PERSON: Final = VERSION.encode()

U64Array = npt.NDArray[np.uint64]


class Stream(IntEnum):
    """Named draw streams. Append only; never renumber (renumbering changes every run)."""

    WORLDGEN = 1
    WEATHER = 2
    GROWTH = 3
    SPOIL = 4
    FIRE = 5
    COMBAT = 6
    TEACH = 7
    EXPERIMENT = 8
    BASELINE = 9
    MOCK = 10
    ORDER = 11
    LIFE = 12
    GARBLE = 13
    TRADE = 14
    BELIEF = 15
    POLITICS = 16
    FISSION = 17
    MORALE = 18


SITES: Final[dict[str, tuple[Stream, int]]] = {
    # Every place in the code that draws registers a unique (stream, n) pair
    # here. Two sites sharing a pair would receive identical numbers.
    "turn_order": (Stream.ORDER, 0),
    "m0_fertility": (Stream.WORLDGEN, 0),
    "m0_camp": (Stream.WORLDGEN, 1),
    "m0_starvation": (Stream.LIFE, 0),
}


def _check_u64(name: str, value: int) -> None:
    if not 0 <= value <= U64_MAX:
        raise ValueError(f"{name} must be an unsigned 64-bit integer, got {value}")


def stream_key(run_seed: int, tick: int, stream: int) -> int:
    """Return the 64-bit key for one stream at one tick of one run."""
    _check_u64("run_seed", run_seed)
    _check_u64("tick", tick)
    _check_u64("stream", stream)
    digest = hashlib.blake2b(
        struct.pack("<QQQ", run_seed, tick, stream), digest_size=8, person=_PERSON
    ).digest()
    return int.from_bytes(digest, "little")


def mix64(z: int) -> int:
    """splitmix64 finaliser: a bijection on 64-bit integers with strong avalanche."""
    z = (z + _GAMMA) & U64_MAX
    z = ((z ^ (z >> 30)) * _C1) & U64_MAX
    z = ((z ^ (z >> 27)) * _C2) & U64_MAX
    return z ^ (z >> 31)


def draw(key: int, entity_id: int, n: int = 0) -> int:
    """Return a uniform 64-bit draw for one entity; ``n`` separates several draws."""
    _check_u64("key", key)
    _check_u64("entity_id", entity_id)
    _check_u64("n", n)
    return mix64(mix64(key ^ entity_id) ^ n)


def _mix64_array(z: U64Array) -> U64Array:
    """Vectorised ``mix64``. uint64 arithmetic wraps modulo 2**64 on every platform."""
    z = z + np.uint64(_GAMMA)
    z = (z ^ (z >> np.uint64(30))) * np.uint64(_C1)
    z = (z ^ (z >> np.uint64(27))) * np.uint64(_C2)
    return z ^ (z >> np.uint64(31))


def draw_array(key: int, ids: U64Array, n: int = 0) -> U64Array:
    """Vectorised ``draw`` over a uint64 id array. Equal to ``draw`` for every id."""
    _check_u64("key", key)
    _check_u64("n", n)
    if ids.dtype != np.uint64:
        raise TypeError("ids must be a numpy uint64 array")
    with np.errstate(over="ignore"):
        return _mix64_array(_mix64_array(np.uint64(key) ^ ids) ^ np.uint64(n))


def uniform_int(u: int, bound: int) -> int:
    """Map a 64-bit draw to ``[0, bound)``. Modulo bias is below bound / 2**64."""
    if bound < 1:
        raise ValueError(f"bound must be >= 1, got {bound}")
    _check_u64("u", u)
    return u % bound


def permutation(key: int, ids: Iterable[int], n: int = 0) -> list[int]:
    """Return ``ids`` shuffled by ``(draw(key, id, n), id)``.

    The result depends only on the set of ids, never on their input order.
    Ties on the draw are broken by id, so the order is total.
    """
    return sorted(ids, key=lambda i: (draw(key, i, n), i))
