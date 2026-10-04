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
| 2026-10-04 | Planning review done; its findings and sources are in `docs/research/80-plan-review-2026-10-04.md` | review |
| 2026-10-04 | **Milestone order accepted** (ADR-0015): foundation, M0 petri dish, M1 seasons and a voice, M2 two tribes, M3 generations, M4 living world, M5 knowledge, M6–M8 society. Replaces the ladder order; births move from the second step to the fourth | creator |
| 2026-10-04 | **Main goal is emergence:** let the models make their own decisions and see what civilization, political system and religion arise; then trace parallels with the real world (ADR-0019) | creator |
| 2026-10-04 | Player contact is a hybrid: buttons for simple acts, free text for complex ones, scriptures, misunderstanding as a feature, possibly speaking only to certain people (ADR-0017) | creator |
| 2026-10-04 | Ideal mind knows how to be a person and wants to live, but knows no technology or history; a pretrained model "pretending to be dumb" is the fallback (ADR-0018) | creator |
| 2026-10-04 | Correction: a 10-tick cadence is 12 councils per civilization per year, not 36; per-year cost figures in ADR-0009 and research notes 30 and 70 are three times too high (ADR-0011) | review |
| 2026-10-04 | `.github/workflows/` stays creator-only by design; agents are not given the Workflows permission (ADR-0016, proposed) | review |
| 2026-10-04 | ADRs 0011–0014 and 0016–0019 accepted | creator |
| 2026-10-04 | **Spending (Q4):** in-game AI is capped at 20 dollars a month in total. Providers: OpenRouter, an Anthropic API key, local Ollama (free). Keys are added by the creator as secrets, never in chat, code or logs | creator |
| 2026-10-04 | Remove the admin bypass on the `main` ruleset, so CI must pass before every merge; the creator changes it in GitHub settings (the session cannot) | creator |
