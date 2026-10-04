# Project status

> Every agent session reads this first and updates it last.

**Phase:** 0, planning complete plus engineering standards; awaiting creator review.
**Last updated:** 2026-10-04 by the standards session (branch `chore/agent-rules-and-team`).

## Current state
- The repo holds docs, ADRs 0001–0010 (Proposed), the CI skeleton and agent conventions. There is no simulation code yet.
- **Rules:** `AGENTS.md` is canonical; `CLAUDE.md` imports it. Path-scoped rules live in `.claude/rules/`.
- **Agent team:** `.claude/agents/` holds architect, test-writer, implementer, reviewer, ui-auditor, researcher and scribe. Model routing is in `docs/agents/agent-team.md` (ADR-0010).
- **Enforcement:**
  - `tools/checks/repo_hygiene.py` and root `ruff.toml`.
  - Claude Code hooks in `.claude/hooks/`, tested by `tools/tests/` (221 tests, including end-to-end script runs).
  - `just check-repo`, plus a prek pre-commit config.
- **CI:**
  - The `repo` job (always on), plus the `docs` and `workflows-lint` jobs, are defined in `ci/workflows/ci.yml`.
  - The `python` and `client` jobs activate when `sim/` and `client/` appear.
  - Workflows still need moving to `.github/workflows/` (see `ci/README.md`).

## Next up (see `docs/plan/roadmap.md` → "Suggested first sprint")
- [ ] Creator: answer `docs/plan/open-questions.md` Q1–Q10 (Q10 = accept ADR-0010).
- [ ] Creator: move `ci/workflows/` to `.github/workflows/` and enable the `main` ruleset (Q6).
- [ ] E1: repo bootstrap. The `sim/` uv project extends `../ruff.toml`; add pyright, pytest-cov gates and the `check-sim` recipe.
- [ ] Client prototype: procedural art, fake replay, Pages demo. Add an eslint config with the AGENTS.md §4.1 limits.
- [ ] Open GitHub issues for E1–E15, then run each with `/tdd <issue>`.

## In flight
_None._

## Known blockers
- No license chosen (Q2).
- No API credentials, so live model qualification is blocked. This is expected and disclosed.
- The workflows are not active until they are moved into `.github/workflows/`.
