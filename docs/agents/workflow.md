# Agent & contributor workflow

## Session lifecycle
1. **Read:** `AGENTS.md` (Claude Code loads it via `CLAUDE.md`), then `docs/agents/STATUS.md`, then the issue, then the relevant ADRs.
2. **Claim:** assign the issue, add the `in-progress` label, and create the branch `agent/<issue#>-<slug>` (or `feat/…`, `fix/…`).
3. **Work** in your own worktree. Keep PRs small: under about 400 changed lines, excluding generated files.
4. **Check:** run `just check`, which is exactly what CI runs.
5. **PR:**
   - The title is a Conventional Commit, e.g. `feat(sim): counter-based RNG`.
   - Fill in the template, including the determinism and schema impact lines.
6. **Hand off:** update `STATUS.md`. If work remains, add `docs/agents/handoff-<slug>.md`, where the slug is the branch name with `/` → `-` (copy `handoff-template.md`). Edit `STATUS.md` only in the PR's final commit, own lines only.

## Hot files: one PR at a time, never mixed with feature work
- `schema/`: the generated contracts. Make a schema-first PR, and merge it before dependent work.
- `uv.lock` and `client/web/package-lock.json`
- `fixtures/golden/`: needs the `golden-update` label, a `RULES_VERSION` bump, and an explanation of the hash diff.
- `rules/`: versioned data; a change bumps the rules version.

## Parallel agents
- **Split along module seams:** `sim/fields`, `sim/agents`, `sim/knowledge`, `cognition`, `persistence`, `client`.
- **Rebase on `main` before opening a PR.** Update a pushed branch with `git push --force-with-lease` (the only allowed force-push). Never push to `main`.

## Definition of done
The canonical checklist is [AGENTS.md §5.4](https://github.com/seedfourtytwo/aimpire/blob/main/AGENTS.md#54-definition-of-done-canonical--the-pr-template-and-dod-mirror-this).
Run `/dod` to check a branch against it. For how work is split between agents and models, see
[agent-team.md](agent-team.md).

## Recommended repo settings (needs admin; see open-questions Q6–Q7)
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

**Pages:** set Source to GitHub Actions.
