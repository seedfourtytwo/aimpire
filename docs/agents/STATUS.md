# Project status

> Every agent session reads this first and updates it last.

**Phase:** foundation done (F1–F6). M0 "petri dish" is built and playable with rule minds; next is running experiment E0 with real models, then M1.
**Last updated:** 2026-10-04 by the planning session (end of day). Handoff: [`handoff-2026-10-04.md`](handoff-2026-10-04.md).

## Current state
- **Goal:** emergence. See what civilizations, political orders and beliefs arise when the models decide for themselves (ADR-0019).
- **Order (ADR-0015):** F1–F6, then M0 petri dish, M1 seasons and a voice, M2 two tribes, M3 generations, M4 living world, M5 knowledge, M6–M8 society. Side tracks: the **Lab** (ADR-0020) and **native minds** (ADR-0021).
- **ADR status:** 0001–0019 accepted. **0020 (Tinkering Lab) and 0021 (native minds) are Proposed** and await the creator, though W0, LAB0 and LAB1 were built at his request.
- **Tests:** about 470, all green; `just check` is what CI runs (about 2 minutes).
- **Repo settings:** `main` is protected (PR required, `ci-ok` required, squash only). The admin bypass and the `protected-change` environment still need the creator (see Known blockers).

## How to play
[`docs/guide/play-m0.md`](../guide/play-m0.md) has the full guide. In short:
```
cd sim && uv sync
uv run aimpire run m0 --mind rule:half_full --seed 1 --years 5 --out ../runs
uv run aimpire run m0 --mind rule:greedy --seed 1 --years 5 --set world.gravity=950000 --out ../runs
uv run aimpire lab twin m0 --set world.gravity=900000 --mind rule:half_full --seeds 1-3 --years 2 --out ../runs/lab
cd .. && python3 -m http.server 8000   # then open client/replay/index.html?src=/runs/<run>/replay.json
```
Minds: `rule:random|greedy|half_full|msy`, `mock`, or a profile (`profiles/ollama-example.toml`, `profiles/anthropic-haiku-4-5*.toml`, the OpenRouter template). Run `aimpire qualify <profile>` before spending money.

## Done
- [x] **F1–F3:** bootstrap, deterministic core, ledger and invariants.
- [x] **F4:** metrics, frames, charts, replay and notebook (#12, #15, #16). F4d playable replay: charts, map overlay, council panel with the mind's verbatim journal (#37).
- [x] **F5:** contracts, providers, places, observation and renderers, validator, council barrier, budgets, run store (#11, #13, #14, #17, #19, #20). Leak fixes: per-civ names; travel through known places only (#22).
- [x] **F6:**
  - live adapters: OpenAI-compatible for Ollama and OpenRouter, and Anthropic, with profiles (#23);
  - `aimpire qualify` and `aimpire batch` (#28).
- [x] **Lab:**
  - W0 world constants and integer physics laws, and LAB0 knob registry and `--set` (#26, #27);
  - LAB1 `aimpire lab twin`; observed travel days follow W0 walking speed (#35);
  - the prototype page is an artifact, not in the repo.
- [x] **M0:**
  - M0a world and regrowth (#30, #31);
  - M0b tribe, work, scouting, hunger (#32);
  - M0c calibration: 1 km tiles, neighbours 1 day apart; baselines; `aimpire run` (#33, #34);
  - M0d reference bands over 200 seeds, and M0e E0 pre-registration (#36).
- [x] **Plans:**
  - Tinkering Lab (#21);
  - native minds (#24);
  - M0 spec (#25);
  - spending: $20 a month, providers OpenRouter, Anthropic and Ollama (#18).

## Next up
- [ ] **Creator:** see the handoff note: accept or amend ADR-0020 and ADR-0021; the GitHub settings; add keys; decide the open items.
- [ ] **E0 pilot:**
  - qualify Ollama `qwen3:8b` on the creator's laptop, then the Ollama pilot file (free);
  - then Haiku, about $5 realistic and under $12 worst case, per `docs/experiments/e0-preregistration.md`.
- [ ] **Small fixes found on the way** (any session):
  - cache place data per tick; about 60 % of run time goes to rebuilding it;
  - guard against two runs writing to the same `--out` folder at once (the spend scan reads a half-created db);
  - `qualify` order-validity is undefined for minds that send no orders, so `rule:half_full` shows FAIL;
  - move protected tests off the `stub` world and the `hold` / `forage_nearest` placeholder rules, then delete them;
  - store OpenRouter's reported cost in the run store, and request usage accounting.
- [ ] **M1:** seasons and a voice (backlog to be specified after E0's pilot). **LAB2** sweeps with M0d machinery. **Native minds** N0–N1 can start now (M0 transcripts exist).

## In flight
- `agent/agent-team-and-guards`: agent team and model routing, Bash guard, repo hygiene ratchet, UI rules (ADR-0022, proposed; open question Q19).

## Known blockers
- `.github/workflows/` is the creator's alone (ADR-0016). Also pending: the always-on `repo` job (backlog G1e, ADR-0022); until it exists, `just check-repo` runs in CI only when the `python` job runs, so PRs touching only `tools/`, `.claude/` or docs skip it.
- The G1a protected-path CI job is ready as a file; the creator adds it after creating the `protected-change` environment.
- The `main` ruleset admin bypass must be removed by the creator in GitHub settings.
- No API keys yet. Live runs need `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY` as environment variables, or a local Ollama.
- `ci.yml`, `dependabot.yml` and the feature issue template still say "E1" and "E5" in comments.
