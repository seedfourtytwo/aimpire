---
description: Check the current branch against the Definition of Done
---
Check the current branch against the Definition of Done in `docs/agents/workflow.md`:

- `just check` passes.
- Tests are added. Invariant-bearing code has property tests.
- The determinism impact is declared, and golden hashes are unchanged or justified.
- The schema is regenerated and the client updated, if contracts changed.
- No network call is added to default or test paths. No credentials appear anywhere.
- Docs and ADRs are updated, and `STATUS.md` is updated.
- CLAUDE.md invariants are respected: sim purity, no `random` or `time` in `sim/`, integer state, sorted iteration.

Report each item as pass or fail with evidence. Fix what you can, then report what remains.
