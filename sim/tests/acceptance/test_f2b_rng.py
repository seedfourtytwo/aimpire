"""F2b acceptance: counter-based draws, version aimpire-draw-v1 (ADR-0012 section B).

Written by the planning model before implementation (ADR-0016). Read-only.
Changing any expected value here changes every stored run: it needs a new ADR.
"""

import numpy as np
import pytest

from aimpire.sim.rng import (
    SITES,
    Stream,
    draw,
    draw_array,
    mix64,
    permutation,
    stream_key,
    uniform_int,
)

pytestmark = pytest.mark.acceptance

# (run_seed, tick, stream, entity, n, key, draw) from the ADR-0012 table.
VECTORS = [
    (0, 0, 0, 0, 0, 9581044940710296089, 7169135194069831215),
    (42, 0, 1, 0, 0, 6975817088793429540, 18296785837534121212),
    (42, 1, 1, 0, 0, 3007589280213941353, 7693534232420839857),
    (42, 1, 2, 0, 0, 2621000684879482037, 2326405843473545382),
    (42, 1, 1, 7, 0, 3007589280213941353, 7745505014182256366),
    (42, 1, 1, 7, 1, 3007589280213941353, 11478825365441001378),
    (2**63, 119, 9, 4095, 3, 4946710756097931948, 14820700008024648776),
    (1, 1_000_000, 3, 123456789, 65535, 11533820859810674773, 16609864973182119386),
]

FROZEN_STREAMS = {
    "WORLDGEN": 1, "WEATHER": 2, "GROWTH": 3, "SPOIL": 4, "FIRE": 5, "COMBAT": 6,
    "TEACH": 7, "EXPERIMENT": 8, "BASELINE": 9, "MOCK": 10, "ORDER": 11, "LIFE": 12,
    "GARBLE": 13, "TRADE": 14, "BELIEF": 15, "POLITICS": 16, "FISSION": 17, "MORALE": 18,
}  # fmt: skip

BUCKETS = 100
CHI2_LIMIT = 160.0  # df = 99; the 99.9% critical value is about 149


@pytest.mark.parametrize("vector", VECTORS)
def test_known_answer_vectors(vector: tuple[int, ...]) -> None:
    seed, tick, stream, entity, n, key, expected = vector
    assert stream_key(seed, tick, stream) == key
    assert draw(key, entity, n) == expected


def test_array_equals_scalar() -> None:
    key = stream_key(42, 5, Stream.GROWTH)
    ids = [*range(5_000), 2**40 + 3, 2**41 + 17, 2**62 + 1, 2**64 - 1]
    arr = draw_array(key, np.array(ids, dtype=np.uint64), 2)
    assert arr.dtype == np.uint64
    assert [int(x) for x in arr] == [draw(key, i, 2) for i in ids]


def _chi2(values: list[int] | np.ndarray) -> float:
    vals = np.asarray(values, dtype=np.uint64)
    counts = np.bincount((vals % np.uint64(BUCKETS)).astype(np.int64), minlength=BUCKETS)
    expected = len(vals) / BUCKETS
    return float(((counts - expected) ** 2 / expected).sum())


def _unit(values: np.ndarray) -> np.ndarray:
    return values.astype(np.float64) / 2.0**64


def test_uniformity_smoke() -> None:
    key = stream_key(42, 5, Stream.GROWTH)
    across_ids = draw_array(key, np.arange(200_000, dtype=np.uint64))
    assert _chi2(across_ids) < CHI2_LIMIT
    assert _chi2([draw(key, 7, n) for n in range(50_000)]) < CHI2_LIMIT
    assert _chi2([draw(stream_key(42, t, Stream.GROWTH), 7) for t in range(50_000)]) < CHI2_LIMIT
    assert _chi2([draw(stream_key(42, 5, s), 7) for s in range(50_000)]) < CHI2_LIMIT

    x = _unit(across_ids)
    assert abs(np.corrcoef(x[:-1], x[1:])[0, 1]) < 0.01
    next_tick = _unit(
        draw_array(stream_key(42, 6, Stream.GROWTH), np.arange(200_000, dtype=np.uint64))
    )
    assert abs(np.corrcoef(x, next_tick)[0, 1]) < 0.01


def test_stream_numbers_frozen() -> None:
    assert {s.name: s.value for s in Stream} == FROZEN_STREAMS


def test_sites_never_share_a_stream_and_n() -> None:
    """One decision site, one (stream, n) pair; sharing one gives identical numbers."""
    pairs = list(SITES.values())
    assert len(pairs) == len(set(pairs))
    assert all(isinstance(stream, Stream) and n >= 0 for stream, n in pairs)


def test_permutation_complete_and_deterministic() -> None:
    key = stream_key(7, 3, Stream.ORDER)
    ids = [5, 1, 99, 42, 7, 1000, 3]
    order = permutation(key, ids)
    assert sorted(order) == sorted(ids)
    assert order == permutation(key, list(reversed(ids)))  # input order never matters
    assert order == sorted(ids, key=lambda i: (draw(key, i), i))
    other = permutation(stream_key(7, 4, Stream.ORDER), ids)
    assert other != order  # a fresh shuffle each tick (holds for this seed)


def test_mix64_and_uniform_int_basics() -> None:
    assert 0 <= mix64(2**64 - 1) < 2**64
    assert uniform_int(17, 5) == 2
    with pytest.raises(ValueError):
        uniform_int(17, 0)


@pytest.mark.parametrize("args", [(-1, 0, 0), (0, -1, 0), (0, 0, -1), (2**64, 0, 0)])
def test_stream_key_rejects_out_of_range(args: tuple[int, int, int]) -> None:
    with pytest.raises(ValueError):
        stream_key(*args)


def test_draw_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        draw(0, -1)
    with pytest.raises(ValueError):
        draw(0, 0, 2**64)
    with pytest.raises(TypeError):
        draw_array(0, np.arange(3, dtype=np.int64))  # pyright: ignore[reportArgumentType]
