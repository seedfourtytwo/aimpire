# Project status

> Every agent session reads this first and updates it last.

**Phase:** planning is done, including the planning review. Next is Phase 1: guard rails, then the foundation. See `docs/plan/roadmap.md` and `docs/plan/backlog.md`.
**Last updated:** 2026-10-04 by the planning review session.

## Current state
- **Goal:** emergence. See what civilizations, political orders and beliefs arise when the models decide for themselves (ADR-0019).
- **Order (ADR-0015, accepted):** foundation F1–F6, then M0 petri dish, M1 seasons and a voice, M2 two tribes, M3 generations, M4 living world, M5 knowledge, M6–M8 society. This replaces the L0–L8 ladder order.
- **Repo contents:** docs, ADRs 0001–0019, active CI, agent conventions, the backlog. There is no code yet.
- **ADR status:** 0001–0019 are all accepted (0011–0019 on 2026-10-04).
- **Repo settings:** `main` is protected (PR required, `ci-ok` required, squash only, linear history). Pages source is GitHub Actions. Workflow token is read-only.

## Next up
- [ ] Creator: answer the remaining items in `docs/plan/open-questions.md`; push G1a (CI path check).
- [ ] G1: guard rails (protected-path hook and CI check, acceptance-test folder). G1a needs the creator.
- [ ] F1: bootstrap the `sim/` uv project. Does not depend on the proposed ADRs.
- [ ] F2: deterministic core (ADR-0011, ADR-0012).
- [ ] F3, then F4 and F5 in parallel, then F6.

## In flight
_None._

## Known blockers
- `.github/workflows/` is the creator's alone, by design (ADR-0016). Workflow changes are pushed by the creator.
- No API keys yet. Live AI runs need a provider key or a local model; nothing before F6 needs one.
- `ci.yml`, `dependabot.yml` and the feature issue template still mention the old epic names "E1" and "E5" in comments. The creator can rename them to F1 when next editing those files.
