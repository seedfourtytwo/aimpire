---
paths:
  - "sim/src/aimpire/sim/**"
  - "rules/**"
  - "fixtures/golden/**"
---

# Simulation core (loaded when touching sim/, rules/ or goldens)

The CLAUDE.md invariants apply strictly here (ADR-0007, ADR-0011, ADR-0012, ADR-0019):

- No `random`, numpy random, `time`, `datetime.now()`, I/O, network or asyncio. Draws come only from
  `aimpire.sim.rng`.
- Integers only in stored or hashed state: milli-units and ppm. Rates go through
  `aimpire.sim.fixed` (carried remainder or a chance draw) — never a bare `//` on a rate.
- Time is data: no literal season or year length; every rate states its period.
- Sequential systems act in the per-tick shuffled order; never rely on set or dict order.
- `sim` imports nothing from `cognition`, `persistence`, `api` or `cli` (import-linter enforces it).
- No enumerated regimes, roles with built-in names or technology trees (ADR-0019).
- Any change to draws, order, rounding or hashing cites ADR-0012 and bumps the rules version; golden
  changes need the `golden-update` label, in their own PR.
- Every invariant you rely on gets a Hypothesis property test.
