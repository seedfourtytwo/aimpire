# ADR-0004: Persistence & replay

- **Status:** Proposed
- **Date:** 2026-10-04
- **Research:** [`docs/research/20-backend-data.md`](../research/20-backend-data.md) §5

## Context
Requirements:
- Recorded replay must reproduce identical checkpoint hashes.
- Branching must carry provenance.
- Every causal link must be inspectable: event → evidence → decision → task → consequence.
- Everything is local-first.

## Decision
- **One SQLite database per run** at `runs/<run_id>/run.db`.
  - WAL mode, `foreign_keys=ON`.
  - SQLite ≥ 3.51.3, asserted at startup because of the WAL-reset corruption fix.
  - One writer (the sim thread); API readers use read-only connections.
- **Content-addressed blob store** `runs/<run_id>/blobs/<sha256>.json.zst` for:
  - raw LLM requests and responses (redacted)
  - prompts
  - checkpoints

  Retention is configurable.
- **The inputs log is the replay source of truth.** It holds interventions plus stored decisions (`parsed_json`), keyed by a deterministic `decision_id`. The sim is a pure step function `state(t+1) = step(state(t), inputs(t))`.
- **Recorded replay** is a new run with `replay_of_run_id`. A `RecordedProvider` returns stored decisions. Every checkpoint hash must match; on the first mismatch it fails loudly, naming the differing subsystem.
- **Fresh rerun** uses the same seed with live providers. It is explicitly *not* hash-comparable and is labelled as such.
- **Branching** copies a checkpoint into a new run database with `parent_run_id`, `branch_tick` and `branch_checkpoint_id`. Future changes are new inputs; history is never edited.
- **The events table is audit output**, not replay input.
- **Checkpoints** are taken every 50 ticks (default) and on demand. Each holds full canonical state, compressed.
- **FTS5** handles memory and claim retrieval, ranked by BM25 with ties broken by id. Embeddings come later, only if an evaluation justifies them, and must stay outside the authoritative path.
- **Migrations** are plain numbered SQL files (`migrations/0001_init.sql`) applied by a small runner. `schema_version` is recorded in the manifest.

## Alternatives considered
- **Pure event sourcing:** every rule would have to be a reducer; too costly.
- **Postgres:** a server dependency, against local-first.
- **A single shared database for all runs:** lock contention and harder export.
- **ORM with Alembic:** unnecessary overhead.

## Consequences
- Replay is cheap and needs no provider.
- Runs are portable: zip the folder.
- Changes to rules or numpy versions invalidate hash comparability, by design. The manifest records both.
