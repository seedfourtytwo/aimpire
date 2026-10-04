# 20 — Backend & Data Architecture

Author: backend/data research lead · 2026-10-04 · Input: `00-brief.md`

## 1. Versions verified (2026-10-04)

| Component | Current | Source |
|---|---|---|
| CPython | **3.14.8** (released 2026-09-30); 3.15.0rc3 out 2026-10-02, final due 2026-10-09 | python.org/downloads/release/python-3148/ · peps.python.org/pep-0790/ |
| uv | 0.12.23 | pypi.org/project/uv |
| ruff | 0.16.10 | pypi.org/project/ruff |
| ty | 0.0.84, **beta** ("no stable API; breaking changes… between any two versions") | github.com/astral-sh/ty |
| mypy / pyright | 2.4.0 / 1.1.414 | PyPI |
| FastAPI / Pydantic / uvicorn | 0.142.2 / 2.13.5 / 0.54.0 | PyPI, fastapi.tiangolo.com |
| numpy | 2.5.3 (requires ≥3.12) | PyPI |
| pytest / hypothesis | 9.1.1 / 6.168.3 | PyPI |
| SQLite | 3.53.4 (2026-07-24); ≥3.51.3 / 3.53.0 needed for the WAL-reset corruption fix | sqlite.org/news.html |
| LiteLLM | 1.104.0, `requires_python <3.15` | pypi.org/project/litellm |
| openapi-typescript | 7.13.0 | npm |

## 2. Language / runtime decision

**Python 3.14, pinned via `.python-version` + `requires-python = ">=3.14,<3.15"`.** Move to 3.15 after ~3.15.2 once numpy/LiteLLM wheels declare support (LiteLLM currently excludes 3.15).

Why Python and not Rust core / TypeScript:
- **Scale is small.** 64² = 4 096 tiles, 256² = 65 536 tiles; 60–500 agents. Per-tick work is O(tiles) vectorizable field updates (soil, moisture, vegetation diffusion) + O(agents) logic. numpy handles 65k-cell arrays in microseconds; agent logic at 500 entities is ~ms in pure Python. Wall-clock is dominated by LLM latency (seconds), not sim.
- **Agent authorship.** Claude Code writes Python + Pydantic + pytest fluently, with the shortest edit/test loop. A Rust core with PyO3 bindings doubles the build surface and slows multi-session iteration for no measured gain.
- **Escape hatch kept:** keep hot field updates behind a `fields/` module with pure-function signatures (`step_hydrology(state_arrays, params) -> arrays`) so it can later be swapped to numba or a Rust extension without touching rules. Only do this when a profile shows >20% of tick time there.
- TypeScript was rejected: its numeric story (no ints beyond 2^53, no numpy) is weak for deterministic fields, and ecosystem for local-model tooling is Python-first.
- Free-threaded 3.14t: not needed (sim is single-threaded by design for determinism; cognition is I/O-bound asyncio).

## 3. Tooling

- **uv** for env, `uv.lock` committed, `uv run` everywhere (CI, scripts, agents). Workspace mode not needed initially (single package).
- **ruff** for lint + format (replaces black/isort/flake8).
- **Type checker: pyright (strict on `sim/`, basic elsewhere) as the CI gate; run ty in CI as non-blocking advisory.** ty is fast and promising but still beta with diagnostics that change between releases — bad for a CI gate maintained across months of agent sessions. mypy is an acceptable alternative; pyright is chosen for speed and better inference on Pydantic v2 without plugins. Revisit when ty reaches 1.0.
- **pytest + hypothesis**: property tests for invariants — conservation of mass for resources (`sum(before) + produced − consumed == sum(after)`), no negative stocks, entity IDs monotone/unique, rejected proposals leave `state_hash` unchanged, `replay(record) == run` hashes. Golden-hash tests per scenario seed pin cross-version determinism.
- pytest-asyncio 1.4 (or anyio) for scheduler tests.

## 4. Simulation core

**Structure: struct-of-arrays for tiles, plain slotted dataclasses (or a light component table) for agents — not a full ECS framework.** ECS libraries (esper etc.) add indirection without benefit at 500 entities and make diffing/serialization less transparent. Use:

- `WorldGrid`: numpy arrays `int32[H,W]` per layer (elevation, water, soil_fertility, vegetation, terrain_kind…).
- `Entities`: dict `EntityId -> Person/Structure/Item` in **sorted-ID iteration order**; components as typed dataclasses with `slots=True`.
- **Stable IDs:** `EntityId = int`, allocated from a per-run monotonic counter stored in state (never `id()`, never uuid4 in sim). Prefix-typed display (`P123`, `S45`) only at the API layer.

**Tick loop (fixed phase order, versioned):**
```
tick(t):
  1. apply_interventions(queued for t)        # god actions, deterministic order by intervention_id
  2. environment phase (weather, season, hydrology, growth)   rng['env']
  3. resolve committed tasks (movement, labor, production)    rng['labor'], agent order = sorted ids
  4. needs/health                                              rng['health']
  5. contact/conflict/trade resolution                         rng['conflict']
  6. perception -> observations (per civ, versioned)
  7. if t % cognition_period == 0: emit cognition requests (barrier)
  8. emit events; state_hash; maybe checkpoint
```

**RNG:** one root `SeedSequence(run_seed)`; spawn named children in a fixed order (`env, labor, health, conflict, perception, mock_cognition, worldgen`), each `Generator(PCG64DXSM(child))`. Per-agent streams only where needed, derived as `SeedSequence(entropy=run_seed, spawn_key=(SUBSYS, agent_id))` so adding an agent doesn't shift others. RNG bit-generator state is part of checkpoints. NumPy only guarantees identical streams on the same build/environment and allows `Generator` method streams to change between versions (numpy.org/doc/stable/reference/random/compatibility.html) — so **pin numpy in the lock, record numpy version in the run manifest, and prefer `integers()` draws** over distribution methods (normal/gamma) in rules.

**Integers for authoritative quantities.** Resources, food, health, labor, water depth are `int` fixed-point (e.g. milli-units: 1 kg grain = 1000). Floats are allowed only in derived/display values and in perception (never fed back into state). This avoids libm/SIMD/FMA differences between machines breaking hashes. Division uses explicit floor/round helpers in `sim/fixed.py`.

**Canonical hashing:** `state_hash = blake2b(canonical_bytes, digest_size=32)` over: rules_version, tick, id counter, RNG states, grid arrays (`arr.astype('<i4').tobytes()` per layer, fixed layer order), entities sorted by ID serialized with msgspec/Pydantic to canonical JSON (sorted keys, no floats), pending tasks, belief/claim store. Exclude wall-clock times, LLM latency, raw outputs. Also hash per-subsystem sub-hashes so divergences are localized quickly.

**Versioned rules:** `RULES_VERSION = "0.3.0"` + content hash of `rules/` data files (transformation recipes, experiment bounds) stored in manifest. Replay refuses on mismatch unless `--allow-rules-drift` (then labeled "fresh rerun").

## 5. Persistence (SQLite)

One SQLite file per run (`runs/<run_id>/run.db`) + `blobs/` dir for large raw payloads (zstd). Per-run files keep branches cheap to copy/export and avoid lock contention. `PRAGMA journal_mode=WAL; synchronous=NORMAL; foreign_keys=ON`. Require SQLite ≥3.51.3 (WAL-reset fix) — assert `sqlite3.sqlite_version` at startup. Writer = single sim thread; API readers use separate read-only connections (WAL allows concurrent readers; sqlite.org/wal.html).

```sql
run_manifest(run_id PK, parent_run_id, branch_tick, branch_checkpoint_id,
  seed, rules_version, rules_hash, code_version(git sha), numpy_version,
  python_version, config_json, mode('research'|'play'), replay_of_run_id, created_at)
civilization(civ_id PK, name, provider, model, model_digest, params_json)
event(event_id PK, tick, seq, kind, payload_json, caused_by_decision_id, caused_by_intervention_id)
observation(obs_id PK, tick, civ_id, observer_entity_id, kind, content_json, source_event_id, obs_version)
cognition_request(request_id PK, round, tick, civ_id, actor_entity_id, context_hash, prompt_blob_ref)
decision(decision_id PK  -- = hash(run_id, round, civ_id, actor_id)
  request_id, provider, model, raw_output_blob_ref, parsed_json, parse_status,
  validation_status, rejection_reason, latency_ms, tokens_in, tokens_out, cost_micros)
task(task_id PK, decision_id, entity_id, kind, params_json, start_tick, end_tick, status, outcome_json)
claim(claim_id PK, civ_id, proposition_json, origin_obs_id, origin_kind, created_tick)
carrier(carrier_id PK, claim_id, holder_kind('person'|'record'|'institution'), holder_id,
  fidelity_milli, confidence_milli, acquired_tick, lost_tick, via_carrier_id)
belief(belief_id PK, entity_id, claim_id, stance, confidence_milli, updated_tick)
memory_fts USING fts5(text, entity_id UNINDEXED, tick UNINDEXED, memory_id UNINDEXED)
intervention(intervention_id PK, tick_applied, kind, params_json, issued_wall_time)
checkpoint(checkpoint_id PK, tick, state_hash, subsystem_hashes_json, state_blob_ref)
schema_migrations(version PK, applied_at)
```

- **Raw LLM outputs** go to `blobs/<sha256>.json.zst` (content-addressed, deduped) referenced from `decision`; only parsed/validated JSON lives inline. This keeps the DB small and makes "replay without providers" just a read of stored `parsed_json`.
- **FTS5** (sqlite.org/fts5.html) for agent memory retrieval: lexical BM25 is deterministic, unlike embedding search; if embeddings are added later, compute them outside the authoritative path and treat ranking ties by memory_id.
- **Migrations: plain numbered SQL files** (`migrations/0001_init.sql`…) applied by a ~50-line runner checking `schema_migrations` (or `PRAGMA user_version`). No SQLAlchemy ORM: the sim doesn't need it, and plain SQL is easier for agents to audit. Alembic (1.20) only if an ORM is later adopted.

### Replay strategy: snapshot + log hybrid
Not pure event sourcing (re-deriving state from events requires every rule to be an event reducer, which is heavy). Instead:
- **Inputs log** is the replay source of truth: interventions + stored decisions (`parsed_json`) keyed by deterministic `decision_id`. Sim is a pure function `state(t+1) = step(state(t), inputs(t), rng)`.
- **Recorded replay**: new run with `replay_of_run_id`, same seed/rules; the cognition provider is swapped for `RecordedProvider` that returns stored decisions by `decision_id`. Every checkpoint's `state_hash` must equal the original; a mismatch fails loudly with the first differing subsystem hash.
- **Events table** is an *output* (audit/inspection trail linking event→observation→decision→task→consequence), not replay input.
- **Checkpoints** every N ticks (default 50) + on demand: full canonical state (msgpack+zstd) + RNG states.
- **Branching**: copy checkpoint into a new run db with `parent_run_id, branch_tick, branch_checkpoint_id`; the new branch's inputs log starts empty after `branch_tick`. Provenance is a tree via `parent_run_id`. "Fresh rerun" = same seed, live providers, new run_id, explicitly not comparable by hash.

## 6. API boundary

**FastAPI (REST for commands/queries) + one WebSocket per client for streaming tick deltas**, bound to `127.0.0.1` by default (fastapi.tiangolo.com/advanced/websockets/).
- REST: `POST /runs`, `POST /runs/{id}/control {pause|step|run}`, `POST /runs/{id}/interventions`, `GET /runs/{id}/entities/{eid}`, `GET /runs/{id}/trace/{event_id}` (causal chain), `POST /runs/{id}/branch`, `GET /runs/{id}/export`.
- WS `/runs/{id}/stream`: messages `{type:"tick", tick, state_hash, deltas:[…], events:[…]}`; deltas are tile-layer patches (changed cells as RLE) + entity upserts/removals. On connect/resync, client gets `snapshot` then deltas; every message carries `tick` so clients detect gaps and request resync. Server never blocks the sim on slow clients (bounded queue, drop-to-resync).
- **Contracts:** Pydantic v2 models in `contracts/` are the single source. Generated artifacts committed under `contracts/generated/`:
  - `openapi.json` (FastAPI) → `openapi-typescript` for a TS research UI.
  - `ws_messages.schema.json` via `pydantic.json_schema.models_json_schema` (JSON Schema 2020-12) for WS messages, which OpenAPI doesn't describe.
  - GDScript: no mature schema→GDScript generator; write a small `scripts/gen_gdscript.py` that walks the JSON Schema and emits typed GDScript classes with `from_dict()`. CI fails if regenerated output differs (`git diff --exit-code`).
  - Contract version field (`api_version`) in every message.
- **Headless CLI** (`gf run|replay|branch|batch|verify`, typer or argparse) calls the same `engine` package directly, no HTTP. Batch experiments = N seeds × configs, each a separate run db, results summarized to a CSV/parquet.

## 7. Async cognition scheduler (sketch)

```python
async def cognition_round(round_no, requests):        # research mode barrier
    async with asyncio.TaskGroup() as tg:
        for civ, reqs in group_by(requests, "civ_id"):
            sem = semaphores[civ.provider_group]          # concurrency group per endpoint
            for r in reqs:
                tg.create_task(run_one(r, sem))
    # all done (or timed out) -> decisions applied in sorted(decision_id) order at tick t+1

async def run_one(r, sem):
    did = decision_id(run_id, round_no, r.civ_id, r.actor_id)   # idempotent
    if (d := store.get_decision(did)): return d                  # resume/replay safe
    async with sem:
        try:
            async with asyncio.timeout(r.timeout_s):
                raw = await provider(r.civ).complete(r.prompt, budget=r.budget)
        except TimeoutError:
            raw = None                                            # -> explicit "no_action", never substitute
    store.put_decision(did, raw, validate(raw, r.obs_version))
```
- Sim does not advance during a research-mode round; in play mode, decisions are applied at the first tick ≥ arrival, but the arrival tick is recorded so replay is still exact.
- Timeouts/parse failures become recorded `no_action` decisions — the record, not timing, drives replay.
- Never call providers from the sim thread; the scheduler runs on the asyncio loop, the sim step runs in a dedicated thread/executor with a single-writer DB connection.

## 8. Proposed package layout

```
greatfilter/
  pyproject.toml  uv.lock  .python-version
  src/greatfilter/
    sim/            # authoritative, pure, no I/O, no asyncio
      state.py ids.py fixed.py rng.py hashing.py tick.py
      fields/ (hydrology.py vegetation.py weather.py)
      agents/ (needs.py labor.py movement.py)
      knowledge/ (claims.py carriers.py beliefs.py perception.py)
      actions/ (schema.py validate.py execute.py)
      rules/ (loader.py, data/*.toml)  # transformation recipes, versioned
    cognition/      # scheduler, providers (mock, rule_based, recorded, litellm), prompts
    persistence/    # db.py migrations/*.sql blobs.py checkpoints.py replay.py
    contracts/      # pydantic API/WS models; generated/ outputs
    api/            # FastAPI app, routes, ws stream
    cli/            # gf command
  tests/ (unit/ property/ golden/ replay/)
  scripts/ (gen_contracts.py gen_gdscript.py)
  docs/adr/
```
Import rule (enforced by ruff `flake8-tidy-imports` banned-api or import-linter): `sim` imports nothing from `cognition/persistence/api`.

## 9. ADR drafts

### ADR-0003 — Backend runtime & tooling
**Status:** Proposed. **Context:** Authoritative deterministic sim, ≤500 agents, ≤256² tiles, LLM-latency bound, primarily written by Claude Code agents across many sessions.
**Decision:** CPython 3.14 (pin `<3.15`; reassess at 3.15.2). numpy for tile fields; integer fixed-point for all authoritative quantities. uv + committed `uv.lock`; ruff lint/format; pyright strict on `sim/` as CI gate, ty advisory; pytest + hypothesis + golden state-hash tests. FastAPI + Pydantic v2 for the API; asyncio for cognition; sim single-threaded and I/O-free.
**Alternatives:** Rust core + PyO3 (rejected: build complexity, no measured need; kept as escape hatch for `sim/fields`); TypeScript/Node (weak numerics, smaller local-LLM ecosystem); ty as gate (beta, unstable diagnostics); ECS framework (unneeded indirection).
**Consequences:** Fast iteration and agent-friendly code; performance ceiling handled by vectorization/numba later; determinism tied to pinned numpy and integer math.

### ADR-0004 — Persistence & replay
**Status:** Proposed. **Context:** Recorded replay must reproduce identical checkpoint hashes; branching with provenance; full causal inspection; local-only.
**Decision:** One SQLite (≥3.51.3, WAL) db per run + content-addressed zstd blob store for raw LLM I/O and checkpoints. Inputs-log (interventions + stored decisions keyed by deterministic `decision_id`) is the replay source; periodic full checkpoints with blake2b canonical hashes + subsystem sub-hashes; events table is audit output. Branch = new run seeded from a parent checkpoint with `parent_run_id/branch_tick`. Plain SQL migrations with a tiny runner. FTS5 for memory retrieval.
**Alternatives:** Pure event sourcing (every rule as reducer — too costly); Postgres (server dependency, against local-first); single shared DB for all runs (contention, harder export); Alembic/ORM (overhead without ORM).
**Consequences:** Replay is cheap and provider-free; divergence localizes to subsystem; schema changes require migration files + manifest `schema_version`; rules/numpy drift invalidates hash comparability by design.

## Sources
- https://www.python.org/downloads/release/python-3148/ · https://peps.python.org/pep-0790/
- https://github.com/astral-sh/ty · https://docs.astral.sh/ty/ · https://docs.astral.sh/uv/ · https://docs.astral.sh/ruff/
- https://numpy.org/doc/stable/reference/random/parallel.html · https://numpy.org/doc/stable/reference/random/compatibility.html
- https://www.sqlite.org/news.html · https://sqlite.org/wal.html · https://sqlite.org/fts5.html
- https://pydantic.dev/docs/validation/latest/concepts/json_schema/ · https://fastapi.tiangolo.com/advanced/websockets/
- https://pypi.org (uv, ruff, ty, mypy, pyright, fastapi, pydantic, numpy, hypothesis, litellm versions) · https://www.npmjs.com/package/openapi-typescript
