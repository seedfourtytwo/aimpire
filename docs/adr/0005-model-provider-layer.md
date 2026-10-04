# ADR-0005: Model provider layer

- **Status:** Accepted
- **Date:** 2026-10-04
- **Research:** [`docs/research/30-model-layer.md`](../research/30-model-layer.md)

## Context
Requirements:
- Many providers, and a different model per civilization in the same run.
- Research-grade fairness and replay.
- Default CI needs no credentials.
- Open-source release.
- Cloud-first development with no GPU.

Constraints found in research:
- LiteLLM had a PyPI supply-chain compromise on 2026-03-24 (versions 1.82.7 and 1.82.8 exfiltrated credentials), and it has a heavy dependency tree.
- Subscription OAuth is not a sanctioned route for in-game calls (see ADR-0009).

## Decision
- **An in-house `Provider` protocol** with methods `complete()`, `describe()` and `estimate_max_cost()`.
- **Adapters, in implementation order:**
  1. `MockProvider`: fixture replies; the CI default.
  2. `RuleProvider`: the scripted baseline.
  3. `RecordedProvider`: replay.
  4. `AnthropicProvider`: official SDK.
  5. `OpenAICompatProvider`: httpx; covers Ollama `/v1`, llama.cpp `llama-server`, OpenRouter and vLLM.
  6. `GeminiProvider`: only on demand.
- **LiteLLM** is an optional, hash-pinned extra `aimpire[litellm]`. It is never imported in the core path or in CI.
- **Structured output:**
  - Use the native JSON-schema mechanism per route.
  - Then validate locally with Pydantic, then with the sim validator.
  - At most **one** schema-repair retry, within the barrier deadline.
  - A semantically invalid action gets no retry; it becomes a recorded `no_action` with reasons.
- **Proposal schema:** one flat `ActionProposal` union discriminated by `kind`. Entity IDs are plain strings validated by the sim.
- **Profiles** are named TOML files in `profiles/*.toml`. Each holds the provider, model, endpoint, `api_key_env`, caps, timeout, concurrency group, and price with source and `as_of`.
- **Metering:**
  - Reserve the maximum cost before dispatch, then reconcile against actual usage.
  - Caps fail closed.
  - An unknown price is reported as `unknown` and needs `allow_unpriced`.
- **No silent fallback.** The resolved model id and digest are recorded per decision. Drift fails a research run unless explicitly allowed.
- **Qualification:** `aimpire qualify <profile>` runs 50 frozen observations × 3 seeds. It reports schema adherence, action validity, latency, tokens and cost.
- **Live evals** run only from a manual workflow in a gated GitHub Environment.

## Consequences
- We maintain about three small adapters ourselves.
- CI stays free and deterministic.
- Players bring their own keys.
- **Revisit if** we need more than five wire formats, or Anthropic sanctions a subscription route for personal apps.
