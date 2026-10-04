# ADR-0009: Funding — the subscription builds, API keys think

- **Status:** Proposed
- **Date:** 2026-10-04
- **Research:** [`docs/research/30-model-layer.md`](../research/30-model-layer.md) §1, §4

## Context
The creator wants to develop in the cloud and use their Claude subscription and roughly $250 of cloud credit as much as possible.

Anthropic's documentation (checked 2026-10-04) says:
- Claude Code cloud sessions bill against the subscription plan.
- Subscription OAuth is for "ordinary use of Claude Code and other native Anthropic applications". Developers building products "should use API key authentication through Claude Console".
- Requests may not be routed through Pro or Max credentials.

The only $250 credit research found was a Claude Code on the web/mobile promotion from November 2025, which was not usable for API calls. The creator's credit may be something else. **Where it appears decides what it can pay for (open question Q3).**

## Decision
- **Building the game** uses the subscription and Claude Code cloud credit: cloud sessions, parallel agents, and optional `@claude` PR reviews.
- **In-game civilization cognition** never uses claude.ai OAuth or subscription credentials. Its options:
  1. **Mock and rule providers.** The default, free, used in all CI.
  2. **A Console API key** (Anthropic), with hard caps in profiles: `per_run_usd`, `per_civ_usd`.
  3. **OpenRouter** for cheap open-weight models, roughly 10–100× cheaper per research.
  4. **Local Ollama or llama.cpp** on the creator's laptop or server.
- If the creator's credit turns out to be **Console API credit**, it funds option 2 directly. Rough cost: one simulated year is about 72 calls, costing $0.72 on Haiku 4.5 and $1.44 on Sonnet 5.5 at current list prices (verify at implementation). $250 covers many experiment sweeps.
- If it is **GCP or AWS credit**, Claude on Vertex AI or Bedrock is a possible later adapter, unverified and dependent on the credit's terms.
- Live-model runs in CI happen only via `eval-live.yml`, a manual dispatch in a gated environment.

## Consequences
- The project is legal to open-source.
- Players bring their own keys or local models.
- Development throughput is limited by plan usage, not dollars.
