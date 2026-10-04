# Project status

> Every agent session reads this first and updates it last.

**Phase:** 0 (planning) is done. Next is Phase 1: engine foundation. See `docs/plan/roadmap.md`.
**Last updated:** 2026-10-04 by the planning session.

## Current state
- **Strategy (ADR-0010):** logic first. Start with simple physics plus an AI in the loop, then climb the complexity ladder L0–L8. Graphics are dots for now.
- **Repo contents:** docs, accepted ADRs 0001–0010, CI workflows (parked in `ci/workflows/` until activated) and agent conventions. There is no code yet.

## Next up
- [ ] Creator: activate CI workflows (move `ci/workflows` → `.github/workflows`, see `ci/README.md`). Enable Pages. Turn on branch protection.
- [ ] F1: repo bootstrap. Create the `sim/` uv project and the justfile `check-sim` recipe.
- [ ] F2: deterministic core and the plug-in system scheduler.
- [ ] F4: dot viewer, metrics and lab notebook.
- [ ] L0: petri dish physics, then the first AI-vs-rules experiment.
- [ ] Research still to write when needed: population/ecology (L1–L3), world-physics fidelity (L2), engine scaling. These tracks were paused at the creator's request.

## In flight
_None._

## Known blockers
- CI workflows are inactive until moved. The Claude GitHub app can't write workflow files.
- No API keys yet. Live AI runs need a provider key or a local model; this is expected.
