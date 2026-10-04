# ADR-0010: Engineering standards and agent model routing

- **Status:** Proposed
- **Date:** 2026-10-04
- **Deciders:** creator
- **Related:** ADR-0006 (repository, CI/CD and agent workflow)

## Context
The creator asked for test-driven development, CI/CD, clean commented modular code with no large
files, Tufte-compliant UI and best practices throughout. They also asked that planning use a
high-reasoning model while code writing uses cheaper agents.

Before this ADR the rules lived in `CLAUDE.md` only, `AGENTS.md` was a pointer, and none of the
size, TDD or UI rules were enforced mechanically.

Claude Code facts verified 2026-10-04 ([subagents](https://code.claude.com/docs/en/sub-agents),
[model config](https://code.claude.com/docs/en/model-config), [hooks](https://code.claude.com/docs/en/hooks),
[memory](https://code.claude.com/docs/en/memory)):
- Subagent frontmatter supports `model` (`opus`, `sonnet`, `haiku`, `fable`, full ID, `inherit`),
  `effort` (`low` … `max`), `tools`, and agent-scoped `hooks`.
- Project `settings.json` supports `model`, `effortLevel` and `env`
  (`CLAUDE_CODE_SUBAGENT_MODEL`).
- When both files exist Claude Code reads `CLAUDE.md`; importing `@AGENTS.md` from it is the
  documented way to share one rulebook with other tools.
- Path-scoped `.claude/rules/*.md` load only when matching files are read or edited.

## Decision
1. **`AGENTS.md` is the canonical, tool-agnostic rulebook.** `CLAUDE.md` imports it and adds only
   Claude Code specifics. The Definition of Done lives in `AGENTS.md` §5.4; the PR template, `/dod`
   and `workflow.md` point to it.
2. **TDD is mandatory** and split across contexts: `test-writer` (red) and `implementer` (green)
   are separate agents. An agent-scoped hook stops `implementer` from editing tests or fixtures.
3. **Model routing:** orchestrator Opus/`high`; `architect` Opus/`xhigh`; `reviewer` Opus/`high`;
   `test-writer`, `implementer`, `ui-auditor`, `researcher` Sonnet/`medium`; `scribe` Haiku/`low`;
   unnamed subagents default to Sonnet. Aliases, not pinned IDs, so the team upgrades with releases.
4. **Mechanical enforcement:**
   - `tools/checks/repo_hygiene.py`: files ≤ 500 lines (target 300), ≤ 500 KB, no run dbs, weights
     or `.env`.
   - Root `ruff.toml`: complexity ≤ 12, ≤ 6 args, ≤ 40 statements, Google docstrings, no
     commented-out code, bandit checks. `sim/` extends it.
   - Claude Code hooks: SessionStart context, Bash guard, post-edit format/size check, Stop
     reminder. Path-scoped rules for sim, client and tests.
   - `just check-repo` runs all of the above. The new always-on CI job `repo` runs it on every PR
     and feeds `ci-ok`. prek runs the same checks as a local pre-commit hook.
5. **Git workflow details:** rebase plus `git push --force-with-lease` is the only force-push allowed,
   and only to feature branches. Red tests are committed before implementation and diffed in review.
   Branch progress lives in per-branch handoff notes; `STATUS.md` is edited only in a PR's final
   commit, own lines only. PR-title scopes gain `tools`, and AGENTS.md mirrors `pr-title.yml`.
   Tool versions are pinned in the `justfile`.
6. **UI standard:** `docs/agents/ui-rules.md` (Tufte integrity and data-ink, traceability,
   Okabe–Ito/viridis, WCAG 2.2 AA), audited by `ui-auditor`.
7. **Shared vocabulary and sources:** `docs/glossary.md` and `docs/references.md`.

## Alternatives considered
- **One model for everything** (Opus or Sonnet only): simpler, but either burns plan usage on
  mechanical work or under-powers planning and review.
- **`opusplan` alias only:** Opus while planning, Sonnet while executing, in one context. Cheaper,
  but no fresh-context review and no TDD role split. Kept as a personal option.
- **Rules only in CLAUDE.md:** other agents (Codex, Copilot) would not see them.
- **Third-party pre-commit hook repos:** extra pinning and supply-chain surface for little gain;
  local hooks call the same tools CI uses.

## Consequences
- Rules are enforced in four places: instructions, path-scoped rules, hooks and CI. CI is the only
  real gate; hooks are guardrails.
- Each TDD step costs extra subagent hand-offs; small edits may be done directly by the orchestrator.
- Hooks need `python3` on PATH (true on the cloud sandbox and Ubuntu; Windows needs Python installed).
- Limits are mirrored in code and in `AGENTS.md` and must change together.
- **Revisit if** Sonnet-produced code repeatedly fails review: raise `implementer` to Opus for
  risky epics. Also revisit when usage limits are hit before epics finish.
