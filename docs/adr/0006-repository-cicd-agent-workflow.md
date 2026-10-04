# ADR-0006: Repository, CI/CD and agent workflow

- **Status:** Proposed
- **Date:** 2026-10-04
- **Research:** [`docs/research/40-cicd-workflow.md`](../research/40-cicd-workflow.md)

## Context
This is a months-long project built mostly by Claude Code agents in cloud sessions, working in parallel with the creator. It is an open-source repo.

Constraints:
- Determinism and backend↔client contracts are non-negotiable.
- No paid infrastructure.
- Default CI needs no LLM credentials.

## Decision
1. **Monorepo** with these top-level directories:
   - `sim/`: Python, a uv project
   - `schema/`: generated contracts, committed
   - `client/web/`
   - `rules/`: versioned data
   - `scenarios/`
   - `profiles/`
   - `fixtures/golden/`
   - `evals/`
   - `tools/`
   - `docs/`
   - `deploy/`
   - `.claude/`
   - `.github/`
2. **GitHub Actions on free hosted runners.**
   - A single path-filtered `ci.yml` with an aggregate `ci-ok` job as the **only required check**.
   - Golden-replay hashes and schema drift are blocking gates.
   - `nightly.yml` runs long seeded batches, compares hashes across Linux and Windows, and tracks benchmark trends.
   - `pages.yml` deploys the docs and the static replay demo.
   - `release-please.yml` handles semver releases.
   - `security.yml` runs CodeQL, dependency review and gitleaks.
   - `eval-live.yml` runs live-model evals on manual dispatch only, behind the `live-eval` environment with a required reviewer and budget caps.
3. **Workflow:**
   - Trunk-based development on short-lived branches (`type/slug`, `agent/<slug>`).
   - Squash merge only.
   - Conventional Commits on PR titles, with scopes `sim, rules, cognition, schema, client, docs, ci, evals`.
4. **Supply chain:**
   - Actions pinned by full SHA with a version comment.
   - Dependabot with a 7-day cooldown.
   - `permissions: {}` at the top of each workflow, granted per job.
   - `persist-credentials: false`.
   - zizmor lints the workflows.
   - OIDC only for Pages and attestations.
5. **Agents:**
   - `CLAUDE.md` plus `.claude/` commands, agents and hooks.
   - One issue, one branch and one worktree per agent.
   - **Hot files are serialized:** `schema/`, `uv.lock`, `fixtures/golden/` and `rules/` changes go in their own small PRs.
   - A definition-of-done checklist.
   - Every session ends by updating `docs/agents/STATUS.md` or writing a handoff note.
   - `claude-code-action` is opt-in (`@claude` mention or label) and never a required check.
6. **Local parity:** CI calls only `just` recipes, so local and CI behaviour match by construction. prek runs the hooks. A devcontainer and Compose (with Ollama) are optional.

## Consequences
- The setup is reproducible and free.
- Determinism regressions are caught at PR time.
- Golden fixtures need disciplined regeneration: label `golden-update` plus a rules version bump.
- Dependabot generates grouped weekly PR noise.
- **Bootstrapping:** today the repo has docs only, so only the docs and workflow-lint jobs run. The `sim` and `client` jobs activate automatically when those directories appear.
