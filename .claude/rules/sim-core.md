---
paths:
  - "sim/src/aimpire/sim/**"
  - "rules/**"
  - "fixtures/golden/**"
---

# Simulation core rules (loaded when touching sim, rules or goldens)

You are in the deterministic, pure core. AGENTS.md §1 and ADR-0007 apply strictly:

- No `random`, numpy `Generator`, `time`, `datetime.now()`, I/O, network or asyncio here. Draws come
  only from `aimpire.sim.rng` (counter-based, keyed by seed, tick, stream, entity id).
- Integers only in stored or hashed state (milli-units, permille). Floats only in derived display.
- Iterate entities in sorted id order; never depend on set or dict ordering of non-integer keys.
- Never import `cognition`, `persistence` or `api` from `sim`.
- Observations must not be able to represent `hidden_cause`, other civs' private data or unseen truth.
- Any behavioural change to rules bumps the rules version; golden fixture changes need the
  `golden-update` label and a justification of the hash diff, in their own PR.
- Every invariant you rely on gets a hypothesis property test.
