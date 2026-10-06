# Agent & contributor workflow

## Session lifecycle
1. **Read:** `CLAUDE.md`, then `docs/agents/STATUS.md`, then the issue, then the relevant ADRs.
2. **Claim:** assign the issue, add the `in-progress` label, and create the branch `agent/<issue#>-<slug>` (or `feat/…`, `fix/…`).
3. **Work** in your own worktree. Keep PRs small: under about 400 changed lines, excluding generated files.
4. **Check:** run `just check`, which is exactly what CI runs.
5. **PR:**
   - The title is a Conventional Commit, e.g. `feat(sim): counter-based RNG`.
   - Fill in the template, including the determinism and schema impact lines.
6. **Hand off:** update `STATUS.md`. If work remains, add `docs/agents/handoff-<branch>.md` (copy `handoff-template.md`).

## Tiers, specs and tests (ADR-0016)
- **Tiers.** The strongest model writes ADRs, interfaces, acceptance tests and reviews. A mid-tier model implements one specified issue. Small models do search and mechanical edits.
- **The issue is the spec.** Use [`task-template.md`](task-template.md). The backlog in `docs/plan/backlog.md` lists the items in build order.
- **Acceptance tests come first.** They live in `sim/tests/acceptance/`, are written by the strong model, and are read-only for implementers.
- **Protected paths.** `sim/tests/acceptance/`, `fixtures/golden/`, `.github/`, `.claude/`, `docs/adr/`, `CLAUDE.md`, lint and type-check settings, and the repo gates (`tools/checks/`, `ruff.toml`, `.pre-commit-config.yaml`). Implementing sessions do not change them.
- **If a test seems wrong, stop and report.** Never edit a test to make it pass.
- **Review.** Changes under `sim/`, `rules/` or `schema/` are reviewed in a fresh session by a stronger model, using [`review-checklist.md`](review-checklist.md).
- **In one session** the tiers are subagents: `/spec` and `/build` route planning, acceptance tests and review to Opus and the coding to Sonnet. See [`agent-team.md`](agent-team.md) (ADR-0022).

## Hot files: one PR at a time, never mixed with feature work
- `schema/`: the generated contracts. Make a schema-first PR, and merge it before dependent work.
- `uv.lock` and `client/web/package-lock.json`
- `fixtures/golden/`: needs the `golden-update` label, a `RULES_VERSION` bump, and an explanation of the hash diff.
- `rules/`: versioned data; a change bumps the rules version.

## Parallel agents
- **Split along module seams:** `sim/fields`, `sim/agents`, `sim/knowledge`, `cognition`, `persistence`, `client`. Inside a milestone, split into physics, observation and prompt, experiment and report.
- **Rebase on `main` before opening a PR.** Update a pushed branch with `git push --force-with-lease`, the only force-push allowed (ADR-0022). Never push to `main`.

## Definition of done
- [ ] `just check` passes (it includes `check-repo`: file limits, forbidden files, hook tests).
- [ ] Tests are added: unit tests, plus property tests for anything that bears an invariant.
- [ ] Determinism impact is declared. Golden hashes are unchanged, or the regeneration is justified.
- [ ] The schema is regenerated if contracts changed, and the client is updated.
- [ ] No network call is added to any default or test path.
- [ ] Docs are updated: domain rules, ADR, README as relevant.
- [ ] `STATUS.md` is updated.

## Recommended repo settings (needs admin)
**Ruleset on `main`:**
- Require a pull request, and require status check `ci-ok`.
- Linear history, squash merge only.
- Block force-pushes and deletion.
- Dismiss stale approvals.

**Settings → Actions:**
- Require actions to be pinned to a full-length commit SHA.
- Default workflow permissions: read.

**Security:** enable secret scanning, push protection and Dependabot alerts.

**Environment `live-eval`:** the creator is the required reviewer. Secrets: `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY` (optional).

**Environment `protected-change`:** the creator is the required reviewer. Used by the protected-path check (backlog G1a).

**Ruleset bypass list:** agents push as the creator's GitHub user, so the creator should not be on it.

**Pages:** set Source to GitHub Actions.
