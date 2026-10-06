# CLAUDE.md — guidance for Claude Code sessions (and humans)

## First, every session
1. Read `docs/agents/STATUS.md` (current phase, what's in flight).
2. Read the issue you're working on, its entry in `docs/plan/backlog.md`, and the ADRs it names (`docs/adr/`).
3. At the end: update `STATUS.md`; if work remains, write `docs/agents/handoff-<branch>.md`.

## What this project is
Aimpire is a deterministic civilization research simulator and god game. Model-driven societies make their own decisions; the simulation validates and executes them; the player is a god who can send signs and speak but never command.

**The goal** is emergence: to see what kind of civilization, political order and belief arises when the models decide for themselves, and to trace parallels with real history. Nothing that is supposed to emerge may be written into the code.

Start with `docs/plan/roadmap.md`. The full intent is in `docs/spec/original-handoff.md`; the reasoning behind the plan is in `docs/research/80-plan-review-2026-10-04.md`.

## Words used here
- **Mind:** one model-driven decision maker. **Council:** one decision turn of a mind.
- **Place:** a named region of the map. Models see places, never tile coordinates.
- **Hearer:** a person the god's voice reaches. The council only hears their report.
- **Preset:** the named configuration of a milestone (`m0`, `m1`, …).
- **Knowledge arm:** how much a mind could know in advance (`A0`–`A3`, ADR-0018).

## Non-negotiable invariants (never violate; stop and ask if a task seems to require it)
- **Authoritative sim.** Model output never mutates state directly. Only validated orders do, through `sim/actions/`.
- **Truth / evidence / belief separation.** Observation types structurally exclude `hidden_cause`, other groups' private data and unseen tile truth. Never add a field that leaks them.
- **Determinism** (ADR-0007, ADR-0012):
  - No `random`, no numpy random, no `time`/`datetime.now()` inside `sim/`. Draws come only from `aimpire.sim.rng`.
  - Integers only in authoritative state: milli-units and ppm. No floats stored or hashed.
  - Rates go through `aimpire.sim.fixed` (carried remainder or a chance draw). No bare `//` on a rate.
  - Sequential systems act in the per-tick shuffled order. Never depend on set or dict order.
- **Time is data** (ADR-0011). No literal season or year length in `sim/`. Rates state their period.
- **The sim package is pure.** `sim/` imports nothing from `cognition/`, `persistence/`, `api/` or `cli/`. It does no I/O.
- **Speech and visions are data.** They appear quoted inside observations, never in system prompts.
- **No pre-baked institutions** (ADR-0019). No enumerated regime, succession or doctrine types; no role with a built-in name; no technology tree. Prompts suggest no institution, belief or strategy. Labels such as "chiefdom" or "priest" exist only in the observer layer.
- **No fabricated emergence.** Never hardcode outcomes or fake events in the UI or demos.
- **No network in default paths.** Tests and CI use mock, rule and recorded providers only. Live calls need explicit profiles plus budgets.
- **Credentials never go in** saves, run dbs, blobs, exports, logs, fixtures or this repo.

## Protected paths (ADR-0016)
`sim/tests/acceptance/`, `fixtures/golden/`, `.github/`, `.claude/`, `docs/adr/`, `CLAUDE.md`, the lint, type-check and import-rule settings (`sim/ruff.toml`, `sim/pyrightconfig.json`, `sim/.importlinter`), and the repo gates (`tools/checks/`, root `ruff.toml`, `.pre-commit-config.yaml`; ADR-0022).
- Sessions meant to edit them (planning and review sessions, the creator) start Claude Code with `AIMPIRE_ALLOW_PROTECTED=1`.
- Implementing sessions do not change these. A new **Proposed** ADR is the one exception.
- **If a test seems to contradict the issue or an ADR: stop. Do not edit the test. Report it in the pull request.**

## Repo layout
Created as epics land.
```
sim/            Python uv project → src/aimpire/{sim,cognition,persistence,contracts,api,cli}
sim/tests/      acceptance/ (read-only for implementers), unit/, property/
schema/         generated contracts (JSON Schema/OpenAPI) — never hand-edit
client/replay/  static replay player; client/web/ comes later
rules/v1/       calendar, rates and transformation rules (versioned data)
scenarios/      scenario and preset files
profiles/       model profile TOML (no secrets — api_key_env names only)
fixtures/golden recorded runs + expected checkpoint hashes
evals/          live-model eval configs (manual workflow only)
docs/           spec, research, adr, architecture, plan, agents, experiments
```

## Commands
Run `just --list` to see them all. Use `just check` before every PR; it is exactly what CI runs.
- `just docs` builds the docs site (strict). `just docs-serve` previews it.
- Python: `lint`, `typecheck`, `test`, `test-fast`, `check-sim`, `schema-check`. Client: `check-client`.
- Repo-wide gates: `just check-repo` (file sizes, forbidden files, tooling and hook tests). It also runs inside `check-sim`.
- Slash commands: `/spec <backlog id>` (S-tier: plan the issue, write acceptance tests first), `/build <issue>` (implement and review), `/fresh-review`, `/ui-review`, `/adr`, `/dod`, `/handoff`.

## Agent team and model routing (ADR-0016, ADR-0022)
The main session is the **orchestrator**: Opus at `high` effort by default (`.claude/settings.json`). It plans and decides, and hands bulk work to subagents in `.claude/agents/`, each pinned to the ADR-0016 tier:

| Agent | Model / effort | Tier | Does |
|---|---|---|---|
| `architect` | opus / xhigh | S | turns a backlog item into an issue (task template), drafts Proposed ADRs |
| `test-writer` | opus / high | S | writes acceptance tests first (strict xfail) and interface stubs |
| `implementer` | sonnet / medium | I | makes them pass, writing its own unit tests first; **can never edit protected paths**, even in an `AIMPIRE_ALLOW_PROTECTED=1` session |
| `reviewer` | opus / high | S | fresh-context review with `docs/agents/review-checklist.md` |
| `ui-auditor` | sonnet / medium | I | Tufte and accessibility audit (`docs/agents/ui-rules.md`) |
| `researcher` | sonnet / medium | I | verifies versions, APIs, prices and model IDs, with URLs and dates |
| `scribe` | haiku / low | small | STATUS, handoffs, logs, doc indexes |

Unnamed subagents default to Sonnet. Details, escalation and how to change the routing: `docs/agents/agent-team.md`.

## Engineering standards (creator)
- **Test-driven.** Acceptance tests exist before the code. Every physics or rule change has a test that would fail without it.
- **Clean, modular, reusable, commented.** Docstrings explain *why* and the units used (milli-units, ppm, per which period).
- **Small files.** Keep a soft cap of about 300 lines per module; split by responsibility before you hit it. The hard limit is 500 lines and 500 KB per file (`tools/checks/repo_hygiene.py`); files over it are listed in `tools/checks/hygiene-baseline.txt` and may only shrink. Function size is a lint rule: pylint defaults in `sim/ruff.toml` (5 arguments, 50 statements, 12 branches); stricter limits plus complexity ≤ 12 and docstrings in the root `ruff.toml` for `tools/` and hooks.
- **Logic before graphics** (ADR-0010, ADR-0015). One milestone at a time. Each is a preset with physics tests, an AI experiment and a replay. Visuals are dots plus charts until the logic earns more.
- **Tufte-style output.** Charts and UI use high data-ink, small multiples and direct labels, with no chart junk. The full rules and the review checklist are in `docs/agents/ui-rules.md`.
- **Never commit** run databases, weights, logs, saves, exports or `.env` files (`repo_hygiene.py` and `.gitignore`); golden fixtures are the one exception.

## Working rules
- One issue, one fresh session, one branch (`agent/<issue>-<slug>`), one small PR. Conventional Commit titles; scopes are listed in `.github/workflows/pr-title.yml`.
- The issue is the spec (`docs/agents/task-template.md`). Stay inside its "In scope" list.
- **Hot files, each in its own PR:** `schema/`, lockfiles, `fixtures/golden/` (label `golden-update` plus a rules version bump), `rules/`.
- **Architecture changes** need a Proposed ADR (`/adr`). The creator accepts it.
- **Verify versions and APIs** against current primary docs before adding dependencies. Never invent model IDs.
- **Show evidence.** Put the `just check` output in the PR. Never mark a partial feature complete.

## Git and GitHub safety (ADR-0022)
A Bash hook (`.claude/hooks/guard_bash.py`) blocks, without the creator's approval in the conversation: pushing to `main` (also implicitly while on `main`), `--all`/`--mirror`, deleting remote branches, tag pushes, force-pushes other than `--force-with-lease` to your own branch, skipping hooks, discarding work (`reset --hard`, `clean -f`, `checkout -- .`, …), reading `.env` or printing credentials, merging or approving PRs, `gh api` writes, `gh workflow run`, releases and visibility changes. It fails open; CI and review remain the real gates. If it blocks something the creator approved, say so and ask the creator to run it.

## Hooks (`.claude/hooks/`, tested in `tools/tests/`)
- **SessionStart:** injects the branch, the session routine, the branch handoff note and the head of `STATUS.md`.
- **PreToolUse:** `protect-paths.py` on edits (ADR-0016); `guard_bash.py` on shell commands.
- **PostToolUse:** formats edited Python in `tools/` and hooks with the pinned ruff and flags files over the hard limit.
- **Stop:** lists protected paths changed (`protect-paths.py stop`) and reminds once to update `STATUS.md` or a handoff note.

