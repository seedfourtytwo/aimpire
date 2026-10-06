# Architecture Decision Records

We use MADR-lite records: one file per decision, `NNNN-kebab-title.md`, copied from [`0000-template.md`](0000-template.md).

**Status lifecycle:** `Proposed` → `Accepted` → (`Superseded by NNNN` | `Deprecated`).

- Any contributor or agent may write a **Proposed** ADR.
- Only the creator moves an ADR to **Accepted**.
- Accepted ADRs are immutable. To change a decision, write a new ADR that supersedes or amends it. The older ADR's status line then gains "amended by NNNN"; its text stays as written.

| # | Title | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-visual-client-stack.md) | Visual client stack: web (PixiJS + React) | Accepted, amended by 0010 |
| [0003](0003-backend-runtime-and-tooling.md) | Backend runtime & tooling: Python 3.14, uv | Accepted |
| [0004](0004-persistence-and-replay.md) | Persistence & replay: SQLite per run, inputs log | Accepted |
| [0005](0005-model-provider-layer.md) | Model provider layer: in-house adapters | Accepted, amended by 0013 and 0014 |
| [0006](0006-repository-cicd-agent-workflow.md) | Repository, CI/CD and agent workflow | Accepted, amended by 0016 |
| [0007](0007-determinism-and-rng.md) | Determinism, RNG and hashing | Accepted, amended by 0012 |
| [0008](0008-first-slice-simulation-scope.md) | First-slice simulation scope (rules v1) | Accepted, amended by 0010, 0011, 0013 and 0017 |
| [0009](0009-funding-development-vs-cognition.md) | Funding: subscription builds, API keys think | Accepted; cost figures corrected in 0011 |
| [0010](0010-complexity-ladder.md) | Logic first, complexity ladder, dot viewer | Accepted; ladder order superseded by 0015 |
| [0011](0011-time-schedules-and-council-cadence.md) | Time, schedules and council cadence | Accepted |
| [0012](0012-numeric-and-random-primitives.md) | Numeric and random primitives | Accepted |
| [0013](0013-mind-interface.md) | The mind interface: places, policy, orders, journal | Accepted |
| [0014](0014-experiment-protocol.md) | Experiment protocol | Accepted |
| [0015](0015-milestone-order.md) | Milestone order | Accepted |
| [0016](0016-agent-guard-rails-and-model-tiering.md) | Agent guard rails and model tiering | Accepted |
| [0017](0017-the-gods-channels.md) | The god's channels: signs, omens, a voice, scripture, prayer | Accepted |
| [0018](0018-what-the-minds-know.md) | What the minds know: knowledge arms and native minds | Accepted |
| [0019](0019-emergence-first.md) | Emergence first: primitives, not institutions | Accepted |
| [0020](0020-tinkering-lab-and-world-constants.md) | The Tinkering Lab and world constants | Accepted |
| [0021](0021-native-mind-track.md) | Native mind track: after M0, generated corpus, constrained replies | Accepted |

Background research for each decision lives in `docs/research/` (listed on the [docs home page](../index.md)).
