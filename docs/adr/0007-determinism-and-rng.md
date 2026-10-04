# ADR-0007: Determinism, RNG and hashing

- **Status:** Proposed
- **Date:** 2026-10-04
- **Research:** [`20-backend-data.md`](../research/20-backend-data.md) §4, [`50-simulation-design.md`](../research/50-simulation-design.md) §0
- **Reconciles:** a conflict between those two reports. Report 20 proposed numpy `SeedSequence`/PCG64 streams; report 50 proposed counter-based hash draws.

## Context
Recorded replay must reproduce identical checkpoint hashes. Proposal arrival order must never change outcomes. NumPy only guarantees identical `Generator` streams on the same build, and distribution methods may change between versions.

## Decision
- **Counter-based RNG.** Every draw is a pure function of its coordinates: `draw(run_seed, tick, stream, entity_id, n) → u64`, computed as BLAKE2b over the canonical tuple.
  - Streams are a fixed enum: `worldgen, weather, growth, spoil, fire, combat, teach, experiment, baseline, mock`.
  - There is no hidden RNG state to checkpoint, and adding a subsystem or an agent never shifts other results.
  - Helpers in `aimpire.sim.rng` provide `uniform_int`, `permille_chance`, `choice` and `permutation` (Fisher–Yates driven by draws).
  - Python's `random` module and numpy `Generator` are **banned in `sim/`**, enforced by a ruff banned-api rule.
- **Integers only in authoritative state.**
  - Quantities are milli-units (1 food unit = 1 person-day = 1000 mu).
  - Probabilities and rates are permille (‰) or ppm.
  - Floats appear only in display or derived values, never stored or hashed.
  - `aimpire.sim.fixed` provides explicit floor-division and rounding helpers.
- **Entity IDs** are integers from a per-run monotonic allocator held in state. Contracts and the UI render them with a type prefix (`P0007`, `S0003`, `CL0102`, `EV0450`). Never `id()` or uuid4.
- **Iteration order:**
  - Entities are always processed in sorted id order.
  - Civilizations are processed in a per-tick seeded permutation.
  - There is no reliance on set or dict ordering of non-integer keys.
- **Hashing:**
  - `state_hash = blake2b-256(canonical bytes)`.
  - Canonical bytes are built from: rules version and hash, tick, id counter, tile layers (`<i4` bytes in fixed layer order), and entities sorted by id as canonical JSON (sorted keys, ints and strings only).
  - Per-subsystem sub-hashes are computed as well, so a divergence is localised.
  - The rolling hash is taken every tick. A full snapshot hash is taken at every cognition barrier and checkpoint.
- **Phase order** follows report 50 §1 (interventions → environment → needs → routine → tasks → conflict → events → memory → checkpoint) and is versioned with the rules.
- **The pinned runtime is recorded** in the manifest: Python, numpy, SQLite and rules versions, plus the git SHA. Nightly CI compares hashes across Linux and Windows.

## Consequences
- Determinism does not depend on numpy's RNG implementation.
- Draws cost a hash each, which is cheap at this scale. Vectorised field noise can use a numpy Philox stream seeded from `draw(...)` per tick-layer, if profiling demands it.
- Permutation-invariance and replay are testable properties.
