# Project status

> Every agent session reads this first and updates it last.

**Phase:** 0, planning complete, awaiting creator review.
**Last updated:** 2026-10-04 by the planning session.

## Current state
- The repo holds docs, ADRs (Proposed), the CI skeleton and agent conventions. There is no code yet.
- CI: the `docs` and `workflows-lint` jobs are active. The `python` and `client` jobs activate when `sim/` and `client/` appear.

## Next up (see `docs/plan/roadmap.md` → "Suggested first sprint")
- [ ] Creator: answer `docs/plan/open-questions.md` Q1–Q7.
- [ ] E1: repo bootstrap (`sim/` uv project, live justfile recipes, `rules/v1` loader).
- [ ] Client prototype: procedural art, fake replay, Pages demo.
- [ ] Open GitHub issues for E1–E15.

## In flight
_None._

## Known blockers
- No license chosen (Q2).
- No API credentials, so live model qualification is blocked. This is expected and disclosed.
