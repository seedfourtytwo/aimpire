# ADR-0012: Numeric and random primitives

- **Status:** Accepted (creator, 2026-10-04)
- **Date:** 2026-10-04
- **Deciders:** creator (proposed by the planning review)
- **Amends:** ADR-0007 (draw function, iteration order, rate units)
- **Research:** [`80-plan-review-2026-10-04.md`](../research/80-plan-review-2026-10-04.md)

## Context
Everything in this ADR changes checkpoint hashes. It must land in F2, before the first golden fixture is recorded. Changing it later invalidates every stored run.

Findings from the review (measured on a cloud machine, CPython 3.14, numpy 2.5.3):

- **Floor division creates dead zones.** A 1 permille per-tick decay stops changing once the value is below 1,000 milli-units. Logistic regrowth cannot restart a tile grazed to near zero.
- **Numpy `int64` arrays overflow without warning.** A product of three large milli-unit values wrapped to a negative number silently.
- **BLAKE2b per draw is fine per agent and slow per tile.** About 0.6 microseconds per draw, against about 10 nanoseconds for an integer mixer over a numpy array.
- **Sorted-id processing gives the oldest ids a standing first-move advantage**, which can pass for inherited advantage or emergent inequality.

## Decision

### A. Fixed-point arithmetic (`aimpire.sim.fixed`)
- Quantities are non-negative integers in milli-units. Scalars are Python `int`. Tile layers are numpy `int64`.
- Rates and chances are in parts per million (`PPM = 1_000_000`), with the period from ADR-0011.
- **Deterministic flows** (decay, regrowth, metabolism, spoilage) use a carried remainder:

```python
def apply_rate(value: int, ppm: int, per_ticks: int, carry: int) -> tuple[int, int]:
    """Return (delta, new_carry) for one tick. Exact: no rate ever rounds to zero."""
    return divmod(value * ppm + carry, PPM * per_ticks)
```

  The carry is stored in state beside the quantity and is part of the state hash.
- **Per-entity events** (a birth, a death, a spark) use a chance draw: `chance_ppm(u, ppm) = (u % PPM) < ppm`.
- **Splitting a remainder fairly** uses `stochastic_round(numer, denom, u)`: floor, plus one with probability `remainder / denom`.
- **Sign rule.** Helpers accept non-negative inputs only and raise `ValueError` otherwise. Debts and deficits are stored as separate non-negative quantities.
- **Overflow rule.** Array helpers assert `values.max() * ppm + PPM * per_ticks < 2**63` and raise `OverflowError`. The assertion is always on.
- **No bare `//` on a rate** in `sim/`. Use the helpers.
- **No absorbing zero.** Any regrowth rule includes a seed term, so an emptied tile recovers. The rule is defined with the M0 rules.

### B. Random draws (`aimpire.sim.rng`), version `aimpire-draw-v1`
Two stages. BLAKE2b separates seeds, ticks and streams. A splitmix64-style finaliser spreads the key over entities.

```python
M = (1 << 64) - 1
GAMMA, C1, C2 = 0x9E3779B97F4A7C15, 0xBF58476D1CE4E5B9, 0x94D049BB133111EB

def stream_key(run_seed: int, tick: int, stream: int) -> int:
    h = hashlib.blake2b(struct.pack("<QQQ", run_seed, tick, stream),
                        digest_size=8, person=b"aimpire-draw-v1")
    return int.from_bytes(h.digest(), "little")

def mix64(z: int) -> int:
    z = (z + GAMMA) & M
    z = ((z ^ (z >> 30)) * C1) & M
    z = ((z ^ (z >> 27)) * C2) & M
    return z ^ (z >> 31)

def draw(key: int, entity_id: int, n: int = 0) -> int:
    """64-bit draw for one entity. n separates several draws for the same entity."""
    return mix64(mix64(key ^ entity_id) ^ n)
```

- `draw_array(key, ids, n=0)` does the same on a numpy `uint64` array and must equal `draw` for every id.
- Reductions: `uniform_int(u, n) = u % n`; `chance_ppm` as above; `permutation(key, ids)` sorts ids by `(draw(key, id), id)`.
- **Streams** are a fixed enum with fixed numbers. Append only; never renumber: `WORLDGEN=1, WEATHER=2, GROWTH=3, SPOIL=4, FIRE=5, COMBAT=6, TEACH=7, EXPERIMENT=8, BASELINE=9, MOCK=10, ORDER=11, LIFE=12, GARBLE=13, TRADE=14, BELIEF=15, POLITICS=16, FISSION=17, MORALE=18`.
- **One decision site, one `(stream, n)` pair.** `rng.py` keeps a registry of the `n` values used per stream. Two sites sharing a pair would draw identical numbers.
- Python's `random`, numpy `Generator` and numpy bit generators stay banned in `sim/`. The Philox allowance in ADR-0007 is withdrawn.

**Known-answer vectors.** The F2 tests must reproduce these exactly.

| run_seed | tick | stream | entity | n | key | draw |
|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | 9581044940710296089 | 7169135194069831215 |
| 42 | 0 | 1 | 0 | 0 | 6975817088793429540 | 18296785837534121212 |
| 42 | 1 | 1 | 0 | 0 | 3007589280213941353 | 7693534232420839857 |
| 42 | 1 | 2 | 0 | 0 | 2621000684879482037 | 2326405843473545382 |
| 42 | 1 | 1 | 7 | 0 | 3007589280213941353 | 7745505014182256366 |
| 42 | 1 | 1 | 7 | 1 | 3007589280213941353 | 11478825365441001378 |
| 9223372036854775808 | 119 | 9 | 4095 | 3 | 4946710756097931948 | 14820700008024648776 |
| 1 | 1000000 | 3 | 123456789 | 65535 | 11533820859810674773 | 16609864973182119386 |

**Statistical smoke test in CI.** Chi-square uniformity over 100 buckets across ids, across ticks, across streams and across `n`; lag-1 correlation across ids; correlation between consecutive ticks. A scratch run of this exact function gave chi-square values of 103 to 115 (99.9% critical value about 149) and correlations under 0.001.

### C. Who acts first
- Each system declares `sequential: true | false`.
- A sequential system processes entities in the order `permutation(stream_key(seed, tick, ORDER), ids)`. A fresh shuffle every tick.
- A non-sequential system updates entities independently and may use any order. Where entities compete for the same thing, the conflict rule is explicit and tested.
- Civilizations keep their per-tick seeded permutation from ADR-0007.

### D. Hashing
- As ADR-0007, with carries included in the canonical bytes.

## Alternatives considered
- **BLAKE2b for every draw** (ADR-0007 as written). Sound, but 30 to 80 times slower on arrays and unusable inside numba if that is ever needed.
- **numpy Philox.** Only its raw stream is stable across versions, and one stream per array ties an entity's number to its position, so a birth shifts every later entity's draw.
- **Stochastic rounding everywhere.** Unbiased but adds variance and a draw per update; kept for per-entity events only.
- **A finer unit (micro-units).** Trades truncation for overflow.

## Consequences
- Scalar draws cost about 1 microsecond in pure Python, array draws about 10 nanoseconds each.
- The mixer is a hash, not a published generator family. The CI smoke test and the BLAKE2b key are the safeguards.
- Each rate-driven quantity carries one extra integer of state.
- Any change to this ADR after the first golden fixture needs a rules version bump and regenerated fixtures.

## References
- Salmon et al., "Parallel Random Numbers: As Easy as 1, 2, 3" (counter-based generators).
- Vigna, splitmix64.
- Lake, spatial agent-based modelling (on fixed execution order).
- Review, rows 2 and 3 of "Blind spots and risks".
