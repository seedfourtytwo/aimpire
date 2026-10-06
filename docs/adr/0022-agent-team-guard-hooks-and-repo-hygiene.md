# ADR-0022: Agent team, guard hooks and repo hygiene

- **Status:** Proposed
- **Date:** 2026-10-06
- **Deciders:** creator (proposed by the standards session)
- **Supersedes / Superseded by:** — (extends ADR-0016; amends nothing it decided)

## Context
The creator asked for rules that keep the project on track from start to end (architecture, workflow,
testing, QA, Tufte-style UI) and for planning on a high-reasoning model with code written by cheaper
agents. ADR-0016 already decides the tiers, acceptance-tests-first and protected paths, but:

- nothing makes a single Claude Code session *use* the tiers: the session model writes everything;
- a session started with `AIMPIRE_ALLOW_PROTECTED=1` to write acceptance tests would also let any
  code it writes touch them;
- shell commands are unguarded beyond a few `permissions.deny` prefixes, and `Bash(gh pr:*)` allows
  `gh pr merge` while agents push as the creator's user;
- "small files" is a soft rule with no check; run data, weights or keys could be committed;
- the Tufte rule is one line, with nothing a reviewer can check against.

Claude Code facts used (docs fetched 2026-10-04: sub-agents, model-config, hooks, memory pages at
code.claude.com): subagent frontmatter takes `model` (`opus`, `sonnet`, `haiku`, `fable`, a full ID
or `inherit`), `effort` (`low` … `max`) and agent-scoped `hooks`; project settings take `model`,
`effortLevel` and `env` (`CLAUDE_CODE_SUBAGENT_MODEL`).

## Decision
1. **Agent team** in `.claude/agents/`, each pinned to its ADR-0016 tier: `architect` (opus, xhigh),
   `test-writer` (opus, high; acceptance tests), `implementer` (sonnet, medium), `reviewer` (opus,
   high; fresh context), `ui-auditor` and `researcher` (sonnet), `scribe` (haiku). The session default
   is opus at high effort; unnamed subagents default to sonnet. Two commands run the ADR-0016 flow:
   `/spec <backlog id>` (S tier, acceptance tests first) and `/build <issue>` (implement, then review).
2. **The implementer can never edit protected paths.** Its frontmatter hook runs `protect-paths.py`
   with `AIMPIRE_ALLOW_PROTECTED=0`, overriding the session. It may write its own unit and property
   tests (ADR-0016 §3).
3. **Bash guard** (`.claude/hooks/guard_bash.py`, `git_rules.py`, `shell_words.py`): parses commands
   (quotes, heredocs, chains, wrappers, substitutions, `bash -c`, `eval`) and denies pushes to `main`,
   `--all`/`--mirror`, remote branch deletion, tag pushes, unsafe force-pushes, skipped hooks,
   discarding work, `.env` reads and printed or literal credentials, PR merge/approve, `gh api`
   writes, `gh workflow run`, releases and visibility changes. **`git push --force-with-lease` to a
   feature branch is allowed**, so a rebased PR can be updated (workflow.md already asks for rebases).
   `permissions` are narrowed to match (no `gh pr merge`, pinned `uvx` tools).
4. **Repo hygiene** (`tools/checks/repo_hygiene.py`): source files ≤ 500 lines (target 300), every
   file ≤ 500 KB, no run databases, weights, logs, saves, exports, keys or `.env` (golden run data
   excepted). Files already over the limit are listed in `tools/checks/hygiene-baseline.txt` with a
   reason and may only shrink (a ratchet). `.gitignore` mirrors the list, anchored at the repo root
   so source folders named `runs/` are not ignored.
5. **Session hooks:** SessionStart injects the routine, the branch handoff note and STATUS;
   PostToolUse formats repo tooling with the pinned ruff and flags oversized files; Stop reminds once
   to record progress.
6. **Gates:** `just check-repo` (hygiene, root-`ruff.toml` lint of `tools/` and hooks, 200+ tests of
   the hooks and checker). It runs inside `check-sim`, so CI enforces it now; a dedicated job is
   backlog G1e for the creator. A prek pre-commit config runs the same checks locally.
7. **UI rules** in `docs/agents/ui-rules.md`: Tufte integrity and data-ink, traceability,
   truth/evidence/belief encodings, observer labels (ADR-0019), colour-blind-safe palettes,
   WCAG 2.2 AA, with a checklist for `ui-auditor`.

## Alternatives considered
- **One model for everything:** simpler, but spends plan usage on mechanical work or under-powers
  planning and review.
- **`opusplan` only:** Opus while planning, Sonnet while executing, in one context. No fresh-context
  review and no separation between test author and implementer. Kept as a personal option.
- **Hard limit with no baseline:** would fail CI today on two protected acceptance files that only an
  S-tier session may split.
- **Block all force-pushes:** forces agents to delete and recreate branches after a rebase, which is
  worse.

## Consequences
- Implementing work stays on Sonnet and planning/review on Opus without the creator switching models.
- Each issue costs a few subagent hand-offs; trivial edits may be done directly.
- Hooks need `python3` on PATH. They fail open; CI and review stay the gates (`docs/limitations.md`).
- Limits are mirrored in code (`repo_hygiene.py`, `ruff.toml`) and in `CLAUDE.md`; change them together.
- **Revisit if** Sonnet-written code often fails review (raise `implementer` for risky items), or plan
  usage runs out before items finish (lower `architect` effort first).

## References
- ADR-0016 and its research note; `docs/agents/agent-team.md`; `docs/agents/ui-rules.md`.
- Claude Code docs: sub-agents, model-config, hooks (code.claude.com, fetched 2026-10-04).
