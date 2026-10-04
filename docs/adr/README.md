# Architecture Decision Records

We use MADR-lite records: one file per decision, `NNNN-kebab-title.md`, copied from [`0000-template.md`](0000-template.md).

**Status lifecycle:** `Proposed` → `Accepted` → (`Superseded by NNNN` | `Deprecated`).

- Any contributor or agent may write a **Proposed** ADR.
- Only the creator moves an ADR to **Accepted**.
- Accepted ADRs are immutable. To change a decision, write a new ADR that supersedes it.

| # | Title | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-visual-client-stack.md) | Visual client stack: web (PixiJS + React) | Proposed |
| [0003](0003-backend-runtime-and-tooling.md) | Backend runtime & tooling: Python 3.14, uv | Proposed |
| [0004](0004-persistence-and-replay.md) | Persistence & replay: SQLite per run, inputs log | Proposed |
| [0005](0005-model-provider-layer.md) | Model provider layer: in-house adapters | Proposed |
| [0006](0006-repository-cicd-agent-workflow.md) | Repository, CI/CD and agent workflow | Proposed |
| [0007](0007-determinism-and-rng.md) | Determinism, RNG and hashing | Proposed |
| [0008](0008-first-slice-simulation-scope.md) | First-slice simulation scope (rules v1) | Proposed |
| [0009](0009-funding-development-vs-cognition.md) | Funding: subscription builds, API keys think | Proposed |
| [0010](0010-engineering-standards-and-agent-routing.md) | Engineering standards and agent model routing | Proposed |

Background research for each decision lives in `docs/research/` (listed on the [docs home page](../index.md)).
