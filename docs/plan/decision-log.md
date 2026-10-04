# Decision & assumption log

One line per decision or assumption: date, item, source. Architecturally significant items have ADRs.

| Date | Decision / assumption | Source |
|---|---|---|
| 2026-10-04 | Research simulator first; mixed models per civ; physical + vision + speech interventions | spec (confirmed) |
| 2026-10-04 | Platform: no creator preference → web client (runs on laptop + phone), see ADR-0002 | creator answer + research |
| 2026-10-04 | Development is cloud-first: Claude Code cloud sessions + GitHub Actions; laptop optional | creator |
| 2026-10-04 | Focus: mix of fun god-game and historical parallels ("the AI will develop its own history") | creator |
| 2026-10-04 | Release model: open-source research | creator |
| 2026-10-04 | Repo/name: `seedfourtytwo/aimpire`; spec title "Great Filter" kept as campaign theme; package `aimpire` | assumption — confirm (Q1) |
| 2026-10-04 | Cognition is never funded via subscription OAuth; API key / OpenRouter / local only (ADR-0009) | research of Anthropic terms |
| 2026-10-04 | Bounded material experiments (not deep physical invention) for v1 | default (spec Q3) |
| 2026-10-04 | One cognition controller per civ; faction minds deferred | default (spec Q4) |
| 2026-10-04 | Creator hardware: Ubuntu laptop 15 GB RAM, RTX 2070 Super Max-Q 8 GB; planned CPU server (+RTX 3060 12 GB later); Windows laptop; iPhone | known context |
| 2026-10-04 | RNG: counter-based BLAKE2b draws, not numpy streams (ADR-0007) | reconciled research 20 vs 50 |
| 2026-10-04 | LiteLLM optional only, due to 2026-03 PyPI compromise (ADR-0005) | research |
| 2026-10-04 | Top-down orthogonal 16 px tiles for v1; isometric later | research 10 |
| 2026-10-04 | No LICENSE file added yet — awaiting creator choice | open (Q2) |
