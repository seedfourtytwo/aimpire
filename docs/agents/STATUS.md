# Project status

> Every agent session reads this first and updates it last.

**Phase:** Phase 1, foundation. F1–F3 are done; next are F4 (watch) and F5 (mind interface) in parallel. See `docs/plan/roadmap.md` and `docs/plan/backlog.md`.
**Last updated:** 2026-10-04 by the F6c/F6d and W0/LAB0 sessions.

## Current state
- **Goal:** emergence. See what civilizations, political orders and beliefs arise when the models decide for themselves (ADR-0019).
- **Order (ADR-0015, accepted):** foundation F1–F6, then M0 petri dish, M1 seasons and a voice, M2 two tribes, M3 generations, M4 living world, M5 knowledge, M6–M8 society. This replaces the L0–L8 ladder order.
- **Repo contents:** docs, ADRs 0001–0019, active CI, agent conventions, the backlog, the `sim/` Python project (F1) and the deterministic core (F2). No world rules yet.
- **ADR status:** 0001–0019 are all accepted (0011–0019 on 2026-10-04).
- **Repo settings:** `main` is protected (PR required, `ci-ok` required, squash only, linear history). Pages source is GitHub Actions. Workflow token is read-only.

## Next up
- [ ] Creator: answer the remaining items in `docs/plan/open-questions.md`; push G1a (CI path check).
- [ ] G1: guard rails (protected-path hook and CI check, acceptance-test folder). G1a needs the creator.
- [x] F1: `sim/` uv project, package skeleton, CLI, guard-rail config and acceptance tests (PR #4).
- [x] F2: deterministic core: `fixed` (F2a), `rng` (F2b), `calendar` and `rules` loader (F2c), `state` and `hashing` (F2d), `scheduler` (F2e). PRs #5–#9.
- [x] F3: ledger and per-system invariant checks (`aimpire.sim.ledger`; scheduler checked mode).
- [x] F4: watch tools: metrics, dot frames, PNG and SVG charts (F4a), replay export and Canvas2D player (F4b), lab notebook (F4c). PRs #12, #15, #16.
- [x] F5: mind interface: contracts and schema (F5a), providers (F5b), places, observation builder and renderers (F5c), validator and decision log (F5d), council barrier, budgets and SQLite run store (F5e). PRs #11, #13, #14, #17, #19, #20. The m0 layout of `civ`, `evidence` and `message` entities is documented in `cognition/civ_record.py`; M0b writes them. Leak fixes (branch `agent/f5c-fix-leaks`): place names are per civilization only (`set_civ_name`), and observed travel times use only known places (`travel_ticks_within`, `lower_bound_ticks`).
- [ ] F6: live adapters (OpenAI-compatible for Ollama and OpenRouter; Anthropic), `aimpire qualify`, `aimpire batch`. Budget rules are under F6 in `backlog.md` (20 dollars a month).
  - F6a/F6b (branch `agent/f6ab-live-adapters`): `OpenAICompatProvider` and `AnthropicProvider` in `cognition/`, profile loader `cognition/profiles.py`, `profiles/*.toml` (Ollama example, Claude Haiku 4.5, OpenRouter template that the loader refuses until filled), `provider_from_profile` in `cognition/live.py`. Tests block real sockets (`sim/tests/conftest.py`). HTTP is `httpx2`, the httpx continuation the `anthropic` SDK now requires.
  - F6c/F6d (branch `agent/f6cd-qualify-batch`): new package `aimpire.experiments`. `aimpire qualify <profile.toml | mock | rule[:name]>` runs the frozen cases in `experiments/data/qualify-cases-v1.json` through the council barrier into a run store and judges them against `qualify-thresholds-v1.toml`; `aimpire batch <experiment.yaml> [--verify]` runs a pre-registered experiment (paired seeds, at least 3 replicates, cyclic seat rotation, renderer and prompt variants, knowledge arm), one run store per run with the file hash in the manifest, and one report with small-multiple charts. Both print the worst case first and refuse over budget (exit 3). Worlds are preset factories (`experiments/worlds.py`); `stub` is a placeholder that M0 replaces by registering `m0`. Rule baselines `hold` and `forage_nearest` live in `cognition/baselines.py`; M0c adds its own there. OpenRouter's `usage.cost` is kept as `reported_cost_micro_usd` on results (not yet stored in the run store).

- [ ] Lab track W0 and LAB0 (ADR-0020, proposed), in review:
  - `rules/v1/world.yaml` (gravity, sunlight, rain, tilt), branch `agent/w0-world-rules`;
  - code, branch `agent/w0-lab0-physics-knobs` (based on it): integer laws in `aimpire.rules.physics` (helpers in `rules/intmath.py`), `DerivedWorld` in `aimpire.sim.derived`, `load_world` and `rules_hash` in `aimpire.rules` (the hash covers every `*.yaml` in the rules dir plus world/rules/tribe overrides), `aimpire.lab` (knobs, overrides, variant, schema), `schema/lab-knobs.schema.json`.
  - No run command exists yet, so `--set` is not on the CLI. M0c calls `aimpire.lab.variant.resolve_variant(rules_dir, args.set)` and `aimpire.lab.overrides.add_set_option(parser)`.

## In flight
_None._

## Known blockers
- `.github/workflows/` is the creator's alone, by design (ADR-0016). Workflow changes are pushed by the creator.
- No API keys yet. Live AI runs need a provider key or a local model; nothing before F6 needs one.
- `ci.yml`, `dependabot.yml` and the feature issue template still mention the old epic names "E1" and "E5" in comments. The creator can rename them to F1 when next editing those files.
