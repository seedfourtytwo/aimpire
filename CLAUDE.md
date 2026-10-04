# CLAUDE.md — guidance for Claude Code sessions (and humans)

## First, every session
1. Read `docs/agents/STATUS.md` (current phase, what's in flight).
2. Read the issue you're working on and the ADRs it touches (`docs/adr/`).
3. At the end: update `STATUS.md`; if work remains, write `docs/agents/handoff-<branch>.md`.

## What this project is
Aimpire is a deterministic civilization research simulator. AI models control civilizations by *proposing* typed actions, and the simulation validates and executes them. The full intent is in `docs/spec/original-handoff.md` and the design in `docs/research/50-simulation-design.md`.

## Non-negotiable invariants (never violate; ask if a task seems to require it)
- **Authoritative sim.** Model output never mutates state directly. Only validated actions do, through `sim/actions/`.
- **Truth / evidence / belief separation.** Observation types structurally exclude `hidden_cause`, other civs' private data and unseen tile truth. Never add a field that leaks them.
- **Determinism** (ADR-0007):
  - No `random`, no numpy `Generator`, no `time`/`datetime.now()` inside `sim/`. Use `aimpire.sim.rng` counter draws only.
  - Integers only in authoritative state: milli-units, permille. No floats stored or hashed.
  - Iterate entities in sorted id order. Never depend on set iteration order.
- **The sim package is pure.** `sim/` imports nothing from `cognition/`, `persistence/` or `api/`. It does no I/O.
- **Speech and visions are data.** They appear quoted inside observations, never in system prompts.
- **No network in default paths.** Tests and CI use mock, rule and recorded providers only. Live calls need explicit profiles plus budgets.
- **Credentials never go in** saves, run dbs, blobs, exports, logs, fixtures or this repo.
- **No fabricated emergence.** Never hardcode outcomes or fake events in the UI or demos.

## Repo layout
Planned; created as epics land.
```
sim/            Python uv project → src/aimpire/{sim,cognition,persistence,contracts,api,cli}
schema/         generated contracts (JSON Schema/OpenAPI) — never hand-edit
client/web/     Vite + React + PixiJS client; src/contract is generated
rules/v1/       authored transformation rules (versioned data)
scenarios/      scenario YAML (shared_river.yaml)
profiles/       model profile TOML (no secrets — api_key_env names only)
fixtures/golden recorded runs + expected checkpoint hashes
evals/          live-model eval configs (manual workflow only)
docs/           spec, research, adr, architecture, plan, agents
```

## Commands
Run `just --list` to see them all. Use `just check` before every PR; it is exactly what CI runs.
- `just docs` builds the docs site (strict). `just docs-serve` previews it.
- Python and client recipes arrive with E1 and the client prototype: `lint`, `typecheck`, `test`, `golden`, `schema-check`, `client-*`.

## Engineering standards (creator)
- **Test-driven.** Write the test first, or with the code. Every physics or rule change has a test that would fail without it.
- **Clean, modular, reusable, commented.** Docstrings explain *why* and the units used (milli-units, permille).
- **Small files.** Keep a soft cap of about 300 lines per module; split by responsibility before you hit it.
- **Logic before graphics (ADR-0010).**
  - Climb the complexity ladder one level at a time.
  - Every new layer is a config-switchable system with validation tests and an AI-behaviour experiment.
  - Visuals are dots plus charts until the logic earns more.
- **Tufte-style output.** Charts and UI use high data-ink, small multiples and direct labels, with no chart junk.

## Working rules
- One issue, one branch (`agent/<issue>-<slug>`), one small PR. Conventional Commit titles with scope `sim|rules|cognition|schema|client|docs|ci|evals`.
- **Hot files, each in its own PR:** `schema/`, lockfiles, `fixtures/golden/` (label `golden-update` plus a rules version bump), `rules/`.
- **Architecture changes** need a Proposed ADR (`/adr`). The creator accepts it.
- **Verify versions and APIs** against current primary docs before adding dependencies. Never invent model IDs.
- **Prefer small, tested increments.** Never mark a partial feature complete.
