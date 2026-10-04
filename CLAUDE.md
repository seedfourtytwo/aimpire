# CLAUDE.md — Claude Code specifics

@AGENTS.md

`AGENTS.md` (imported above) is the canonical rulebook. This file adds only what is specific to
Claude Code. Do not restate rules here; change `AGENTS.md` instead.

## How a session runs

You are the **orchestrator**. The project default is Opus at `high` effort (`.claude/settings.json`)
so planning, decomposition and judgement get the strongest reasoning. Hand bulk work to the
cheaper subagents below and keep your own context for decisions.

For each issue, run the loop (or use `/tdd <issue>`):

1. **Plan** — for anything beyond a one-file change, delegate to `architect` (Opus, `xhigh`). Use
   plan mode for schema, rules-version, determinism or cross-module changes. Get back: behaviours
   to test, file map, ordered steps that each fit one PR, invariants touched.
2. **Red** — delegate to `test-writer` (Sonnet). Confirm it reports the failing run and that each
   test fails for the expected reason.
3. **Green** — delegate to `implementer` (Sonnet). A hook blocks it from editing tests/fixtures; if
   it reports a test is wrong, decide yourself (or ask `architect`) before anything changes.
4. **Review** — delegate to `reviewer` (Opus, fresh context) for every PR; add `ui-auditor` for
   client changes. Fix blocking findings via `implementer`, then re-review.
5. **Wrap up** — run `just check` yourself and read the real output; delegate STATUS/handoff
   chores to `scribe` (Haiku); open the PR.

Other delegation: `researcher` for any version, API, price or model-ID question (with URLs and
dates); the built-in `Explore` agent for broad code searches. Run independent subagents in
parallel; never let two agents edit the same file. Small, obvious edits (a typo, one-line fix) you
may do directly — still test-first.

## Agent team (`.claude/agents/`) — details in `docs/agents/agent-team.md`

| Agent | Model / effort | Writes code? |
|---|---|---|
| `architect` | opus / xhigh | docs and ADR drafts only |
| `test-writer` | sonnet / medium | tests + interface stubs |
| `implementer` | sonnet / medium | production code (tests blocked by hook) |
| `reviewer` | opus / high | no — read-only findings |
| `ui-auditor` | sonnet / medium | no — read-only findings |
| `researcher` | sonnet / medium | no — cited findings |
| `scribe` | haiku / low | docs, STATUS, handoffs, changelog |

Unnamed subagents default to Sonnet (`CLAUDE_CODE_SUBAGENT_MODEL`).

## Commands

- `/tdd <issue>` — full plan → red → green → review loop
- `/fresh-review` — fresh-context review of the current branch (built-in `/review` is different)
- `/ui-review` — Tufte/accessibility audit of client changes
- `/adr <title>` — draft a Proposed ADR
- `/dod` — check the branch against the Definition of Done
- `/handoff` — end-of-session STATUS update and handoff note

`just --list` shows all recipes; `just check` is exactly what CI runs.

## Path-scoped rules (`.claude/rules/`)

Loaded automatically when you read or edit matching files: `sim-core.md` (sim, rules, goldens),
`client-ui.md` (client), `tests.md` (any test file). They condense the relevant AGENTS.md sections.

## Hooks (`.claude/hooks/`, tested in `tools/tests/`)

- **SessionStart** — injects the branch, the session routine and the head of `STATUS.md`.
- **PreToolUse(Bash)** — `guard_bash.py` blocks force-push, pushes to `main`, `--no-verify`,
  destructive git, reading `.env`, literal keys, releases and visibility changes.
- **PostToolUse(Edit|Write)** — formats Python with ruff (if installed) and flags files over the
  500-line limit.
- **Stop** — reminds once per session to update `STATUS.md` when code changed.

Hooks require `python3` on PATH. If a hook blocks something the creator has explicitly approved in
this conversation, say so and ask the creator to run it.

## Reporting back

Lead with what works and how it was verified (real command output). List what was not validated.
Keep it short; the PR and `STATUS.md` hold the detail.
