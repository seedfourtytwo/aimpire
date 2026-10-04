# Decision & assumption log

One line per decision or assumption: date, item, source. Architecturally significant items have ADRs.

| Date | Decision / assumption | Source |
|---|---|---|
| 2026-10-04 | Research simulator first; mixed models per civ; physical + vision + speech interventions | spec (confirmed) |
| 2026-10-04 | Platform: no creator preference → web client (runs on laptop + phone), see ADR-0002 | creator answer + research |
| 2026-10-04 | Development is cloud-first: Claude Code cloud sessions + GitHub Actions; laptop optional | creator |
| 2026-10-04 | Focus: mix of fun god-game and historical parallels ("the AI will develop its own history") | creator |
| 2026-10-04 | Release model: open-source research | creator |
| 2026-10-04 | Name: **Aimpire** everywhere (package `aimpire`); "Great Filter" is only an in-game challenge | creator |
| 2026-10-04 | Cognition is never funded via subscription OAuth; API key / OpenRouter / local only (ADR-0009) | research of Anthropic terms |
| 2026-10-04 | Bounded material experiments (not deep physical invention) for v1 | default (spec Q3) |
| 2026-10-04 | One cognition controller per civ; faction minds deferred | default (spec Q4) |
| 2026-10-04 | Creator hardware: Ubuntu laptop 15 GB RAM, RTX 2070 Super Max-Q 8 GB; planned CPU server (+RTX 3060 12 GB later); Windows laptop; iPhone | known context |
| 2026-10-04 | RNG: counter-based BLAKE2b draws, not numpy streams (ADR-0007) | reconciled research 20 vs 50 |
| 2026-10-04 | LiteLLM optional only, due to 2026-03 PyPI compromise (ADR-0005) | research |
| 2026-10-04 | Top-down orthogonal 16 px tiles for v1; isometric later | research 10 |
| 2026-10-04 | License: Apache-2.0 | creator |
| 2026-10-04 | Cloud credit + subscription fund **coding** only; game AI uses direct provider API keys or local models | creator |
| 2026-10-04 | ADRs 0002–0009 accepted; **ADR-0010**: logic first — simple physics + AI in the loop, then a complexity ladder L0–L8; dots before graphics | creator |
| 2026-10-04 | Standards: TDD, clean modular commented code, small files (~300 lines), CI/CD, Tufte-style charts/UI | creator |
| 2026-10-04 | Births/aging, ecology, disease are in scope early (ladder L1–L3), reversing ADR-0008's deferral | creator |
