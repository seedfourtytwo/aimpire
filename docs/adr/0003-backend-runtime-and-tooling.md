# ADR-0003: Backend runtime & tooling

- **Status:** Accepted
- **Date:** 2026-10-04
- **Research:** [`docs/research/20-backend-data.md`](../research/20-backend-data.md)

## Context
The simulation is authoritative and deterministic. Scale is ≤500 agents on ≤256² tiles, and LLM latency dominates wall-clock time. Code will be written primarily by Claude Code agents across many sessions.

## Decision
- **CPython 3.14**, pinned via `.python-version` and `requires-python = ">=3.14,<3.15"`. Reassess at 3.15.2.
- **numpy** for tile-layer fields. **Integer fixed-point** for every authoritative quantity (see ADR-0007).
- **Tooling:**
  - **uv** with a committed `uv.lock`; CI runs `uv sync --locked`.
  - **ruff** for lint and format.
  - **pyright** as the type-check gate: strict on `sim/`, basic elsewhere. **ty** runs advisory only while it is pre-1.0.
  - **pytest + hypothesis** for property tests, plus golden state-hash tests.
- **FastAPI + Pydantic v2** for the API, and **asyncio** for cognition I/O.
- **The simulation package is pure:** single-threaded, with no I/O and no asyncio. An import rule bans `sim` from importing `cognition`, `persistence` or `api`.
- **Package layout:** `sim/src/aimpire/{sim,cognition,persistence,contracts,api,cli}`. The CLI entry point is `aimpire`, with short alias `aim`.

## Alternatives considered
- **Rust core with PyO3:** build complexity with no measured need. Kept as an escape hatch behind `sim/fields/`.
- **TypeScript/Node:** weak integer numerics and a Python-first local-LLM ecosystem.
- **ty as the gate:** still beta, and its diagnostics change between releases.
- **An ECS framework:** unneeded indirection at this scale.

## Consequences
- Fast iteration in a stack agents handle well.
- If performance becomes an issue, vectorise or use numba or Rust in `fields/` only after profiling shows more than 20% of tick time there.
