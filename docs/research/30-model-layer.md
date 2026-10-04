# 30 — Model provider layer (LLM integration)

Research lead: LLM integration · 2026-10-04 · Status: proposal. Every model ID and price below was **seen in a cited page on 2026-10-04; verify at implementation**.

## 1. What the subscription/credit can pay for (read first)

| Spend | Paid by Claude Pro/Max subscription or Claude Code credit? | Source |
|---|---|---|
| Claude Code sessions (CLI, web/cloud, mobile) that **write the game's code** | **Yes.** Counts against plan limits; "no separate compute charge for the cloud VM". | [cloud docs, Limitations](https://code.claude.com/docs/en/claude-code-on-the-web) |
| **In-game civ cognition** (the game calling Claude) via Agent SDK, `claude -p`, or an OAuth/`setup-token` token | **No, not a sanctioned route.** OAuth "is designed to support ordinary use of Claude Code and other native Anthropic applications"; developers building products, "including those using the Agent SDK, should use API key authentication through Claude Console". Third parties may not "route requests through Free, Pro, or Max plan credentials". Pro/Max limits "assume ordinary, individual usage". | [legal-and-compliance](https://code.claude.com/docs/en/legal-and-compliance); [Agent SDK overview note](https://code.claude.com/docs/en/agent-sdk/overview) |
| Same, for an open-source release where *players* bring Claude | Players must use their **own Console API key** (or Bedrock/Vertex/Foundry). We must never ship claude.ai login. | same |
| GitHub Actions live evals | Need a **Console API key** (secret). `claude --bare -p` "never reads OAuth credentials"; it needs `ANTHROPIC_API_KEY`. | [headless docs](https://code.claude.com/docs/en/headless) |

Background: on 2026-02-19 Anthropic clarified that subscription OAuth may not be used by third-party tools ([GIGAZINE](https://gigazine.net/gsc_news/en/20260220-anthropic-third-party-block)). From 2026-04-04, subscription limits stopped covering third-party harnesses such as OpenClaw; the paid route for those became pay-as-you-go extra usage, usage bundles, or the API ([TechRadar](https://www.techradar.com/pro/bad-news-claude-users-anthropic-says-youll-need-to-pay-to-use-openclaw-now)). One April 2026 extra-usage credit promo said its credit worked "across Claude, Claude Code, Claude Cowork, and third-party products" and excluded Console accounts ([support 14246053](https://support.claude.com/en/articles/14246053)). **Unclear:** whether subscription *extra usage* may legitimately pay for a self-built game harness. The developer docs above still say "use API keys". Treat it as not available unless Anthropic sales confirms in writing.

**The "$250 cloud credit".** The only $250 credit I can find is the Claude Code promotion: "$250 in credits at API pricing" for Pro and $1000 for Max. It was claimable 2025-11-04→2025-11-22 and expired 2025-11-22 23:59 PT. It was usable **"only for Claude Code on the web and mobile"**, not the API ([support 12690958](https://support.claude.com/en/articles/12690958-claude-code-promotion)). Later promos either raised Claude Code weekly limits (50% from 2026-05-13 to 09-13, then 25% permanently; [support 15910845](https://support.claude.com/en/articles/15910845)) or excluded Console. I found **no current promo that funds API calls**. If the creator holds a $250 balance, check where it shows. Credit in the **Claude Console billing page** pays for API cognition. Credit tied to the claude.ai plan pays only for Claude Code development. If it is GCP/AWS cloud credit, Claude on Vertex AI/Bedrock may be payable from it; that is unverified and depends on the credit's terms. Claude for Open Source gives Max 20x for 6 months, not API credit ([terms](https://www.anthropic.com/claude-for-oss-terms)).

**Recommendation.** Spend the subscription/credit on building (cloud sessions, many agents). Fund cognition with a small, capped Console key, and with OpenRouter/local open-weight models, which cost ~10–100× less (§4).

## 2. Adapter strategy: thin in-house adapters, LiteLLM optional extra

LiteLLM is active (1.104.0 released 2026-10-03, `requires_python <3.15`; [PyPI](https://pypi.org/project/litellm/)). Two problems:
- **Supply chain:** on 2026-03-24, litellm 1.82.7/1.82.8 on PyPI were backdoored through a compromised maintainer account and CI. 1.82.8 shipped a `.pth` file that ran at interpreter start and exfiltrated API/cloud/SSH keys ([NetSPI](https://www.netspi.com/blog/executive-blog/ai-ml-pentesting/litellm-supply-chain-compromise/)).
- **Weight:** core dependencies include `openai`, `tokenizers`, `huggingface-hub`, `tiktoken`, `aiohttp`, `jinja2`, and `boto3` (PyPI metadata), with release-candidate cadence ≈ daily.

We need only ~3 wire formats. **Decision:** in-house adapters on `httpx`, plus the official `anthropic` SDK (and optionally `openai`) behind our own Protocol. `litellm` is an opt-in extra (`gf[litellm]`), hash-pinned with `uv --require-hashes`, and never imported in the core path or CI.

```python
class Provider(Protocol):
    id: str                                   # "anthropic", "openai_compat:ollama-laptop"
    async def complete(self, req: CognitionRequest) -> CognitionResult: ...
    async def describe(self) -> ModelIdentity   # resolved model id/digest, ctx, caps
    def estimate_max_cost(self, req: CognitionRequest) -> Money | None   # None = unknown price

@dataclass(frozen=True)
class CognitionRequest:
    decision_id: str; civ_id: str; obs_version: int
    system: str; cacheable_prefix: str; observation: str     # stable prefix first for caching
    schema: dict                                             # JSON Schema from Pydantic ActionProposal
    max_output_tokens: int; temperature: float; seed: int | None; timeout_s: float

@dataclass(frozen=True)
class CognitionResult:
    raw_text: str; parsed: dict | None; status: Literal["ok","schema_fail","refusal","timeout","truncated","error"]
    usage: Usage   # in, out, cache_read, cache_write, reported_cost|None
    model_reported: str; latency_ms: int; attempts: int
```

First adapters, in order:
1. `MockProvider` (fixture replies keyed by `decision_id`; CI default)
2. `RuleProvider` (scripted baseline)
3. `RecordedProvider` (replay; see 20-backend)
4. `AnthropicProvider`
5. `OpenAICompatProvider`, configured per endpoint for Ollama `/v1`, llama.cpp `llama-server`, OpenRouter, vLLM
6. `GeminiProvider` later, only if a user asks

## 3. Structured output per route

| Route | Mechanism (2026-10) | Guarantee / caveats |
|---|---|---|
| Anthropic | `output_config.format: {type: "json_schema", ...}` (GA), or `strict: true` tools. Old `output_format` + beta header deprecated. | Constrained output. Exceptions: refusal, `max_tokens`. No `minimum/maxLength/pattern` (move them to descriptions, validate locally). First request pays grammar compile; grammar cached 24h; **changing the schema invalidates the prompt cache.** [docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) |
| OpenAI / compat | `response_format: {type: "json_schema", json_schema: {strict: true, schema}}`. Strict needs all fields `required`, `additionalProperties: false`. | [docs](https://developers.openai.com/api/docs/guides/structured-outputs) |
| OpenRouter | Same `response_format`, plus `provider.require_parameters: true`. | Support is **per endpoint**; "exact compliance is not guaranteed on every endpoint". [docs](https://openrouter.ai/docs/features/structured-outputs) |
| Ollama | Native `format: <JSON Schema>`; also `/v1` `response_format`. | Docs advise also putting the schema in the prompt and using temp 0. Not supported on Ollama Cloud. [docs](https://docs.ollama.com/capabilities/structured-outputs) |
| llama.cpp | `/completion` `json_schema` or `grammar` (GBNF); `/v1/chat/completions` `response_format` json_schema. | External `$ref`: convert with `json_schema_to_grammar.py`. [README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) |
| Gemini | JSON mime type + schema. | Subset of JSON Schema; deeply nested schemas may be rejected. [docs](https://ai.google.dev/gemini-api/docs/structured-output) |

**Schema design:** one flat `ActionProposal` union, discriminated by `kind` as an enum, with ≤24 optional params (Anthropic strict limit). IDs are plain strings validated by the sim, since enums of live entity IDs would break grammar caching.

**Repair policy (bounded, recorded):**
- Parse → Pydantic validate → sim validate.
- On *schema* failure: one repair retry, sending the validator error and the original reply with `max_output_tokens` unchanged, inside the same barrier deadline.
- On *sim-semantic* invalidity (wrong ID, missing prerequisite): no retry. Record an explicit `no_action` with reasons. This is game-visible (“the elders could not agree”).
- Every attempt is stored as a blob. `attempts` and `status` are research metrics.

**Qualification suite (`gf qualify <profile>`):** 50 frozen observation fixtures × 3 seeds. Reports:
- schema-adherence %
- sim action-validity %
- p50/p95 latency
- tokens in/out, $/call
- refusal and truncation rate

A profile is "research-qualified" at ≥98% schema adherence and ≥85% action validity (initial thresholds). The result is stored with the model digest, and runs record which qualification they used.

## 4. Cost realism

Assumptions: 5k tokens in (3k stable prefix with rules/persona/schema, 2k fresh observation), 1k out. 2 civs × 36 rounds = **72 calls per simulated year** (one call per civ per round; per-agent calls multiply this). Prices per MTok from [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing) and [models](https://platform.claude.com/docs/en/about-claude/models/overview); OpenRouter model pages ([gpt-oss-120b](https://openrouter.ai/openai/gpt-oss-120b), [qwen3-235b-a22b-2507](https://openrouter.ai/qwen/qwen3-235b-a22b-2507)); lowest-priced endpoint, which varies.

| Model (ID seen) | $ in/out | $/call | $/sim-year (72) | cached prefix | Batch (−50%) | Years per $250 at 72 calls/yr | Years at 10× calls (per-leader calls) |
|---|---|---|---|---|---|---|---|
| Haiku 4.5 `claude-haiku-4-5-20251001` | 1 / 5 | 0.010 | $0.72 | $0.53 | $0.36 | ~350 | ~35–48 |
| Sonnet 5.5 `claude-sonnet-5-5` | 2 / 10 | 0.020 | $1.44 | $1.05 | $0.72 | ~170 | ~17–24 |
| Opus 5.5 `claude-opus-5-5` | 4 / 20 | 0.040 | $2.88 | $2.06 (5% read) | $1.44 | ~87 | ~9–12 |
| gpt-oss-120b (OpenRouter) | 0.03 / 0.17 | 0.0003 | $0.02 | — | — | ~10,000 | ~1,000 |
| qwen3-235b-a22b-2507 (OpenRouter) | 0.0875 / 0.35 | 0.0008 | $0.06 | — | — | ~4,400 | ~440 |

Pricing notes:
- Cache reads cost 0.1× input (0.05× on Opus 5.5).
- Cache writes cost 1.25× for 5-minute entries and 2× for 1-hour entries. Minimum cacheable length is 512 tokens on current models.
- Caching works with Batch ([caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)).
- A barrier round takes roughly 10–60 s, so the 5-minute TTL stays warm.
- Adaptive thinking on Sonnet/Opus 5.5 adds output tokens. Cap them through `max_output_tokens` in the profile and measure in qualification.

**Batch API** does not fit the interactive barrier, since results can take up to hours. It does fit offline **sweeps** run in round lockstep: submit all civs' round-N requests for M parallel seeds as one batch, wait, apply, then submit N+1. The barrier semantics are preserved because world time is decoupled from wall time.

Conclusion: model price is not the constraint for the first slice. Call fan-out (per-agent versus per-civ cognition) and thinking tokens drive cost.

## 5. Local inference (user-side, not CI)

- **8 GB** (RTX 2070 Max-Q): 4–8B models at Q4. Examples: `qwen3:8b` 5.2 GB, `gemma3:4b` 3.3 GB ([Ollama library](https://ollama.com/library/qwen3); [gemma3](https://ollama.com/library/gemma3)).
- **12 GB** (RTX 3060): up to ~12–14B models (`gemma3:12b` 8.1 GB, `qwen3:14b` 9.3 GB) with modest context.
- **CPU server:** MoE models with few active parameters are tolerable but slow. Size the barrier timeout from qualification p95.
- **Two models at once in Ollama:** `OLLAMA_MAX_LOADED_MODELS` loads several "provided they fit in available memory" (default 3 per GPU). `OLLAMA_NUM_PARALLEL` defaults to 1. RAM scales with `NUM_PARALLEL × CONTEXT_LENGTH` ([FAQ](https://docs.ollama.com/faq)).
  - On 8 GB, two 4B models fit. A 4B + 8B pair will spill or swap.
  - Set `OLLAMA_KEEP_ALIVE=24h` so the barrier doesn't pay reload time.
  - For fairness experiments, prefer one model per machine (laptop + server), with each civ's provider in its own concurrency group.
  - llama.cpp `--models-dir` router mode is an alternative.

## 6. Budgets, metering, fairness, secrets

**Reserve before dispatch:**
- `max_cost = in_tokens × in_price + max_output_tokens × out_price × (1 + repair_retries)`, reserved against per-call, per-civ, and per-run caps.
- If any cap would be exceeded, refuse dispatch. The civ gets a recorded `budget_exhausted` decision, and the run pauses in research mode.

**Reconcile:** replace the reservation with actual usage, cache tokens, and the provider-reported cost when available. Store both values. Show drift in the UI.

**Unknown price** (local or new model): the `estimate` is `None`. The profile must declare `price: {unknown: true}`. Token caps still apply, and a cost cap fails closed unless `allow_unpriced=true`.

**Fairness barrier:**
- Same `max_output_tokens`, same timeout, and same observation budget for every civ in a run.
- Latency is recorded but never converted into extra turns.
- Retries count against the civ's own deadline.

**No silent fallback:** a profile pins `provider` and `model`, and stores the resolved `model_reported` and digest. A mismatch (for example, OpenRouter routing to a different endpoint, or an Ollama digest change) is flagged in the run manifest. In research mode it fails the run unless `allow_model_drift`. A substitute is only ever an explicit config change, recorded as an input event.

**Secrets:**
- Keys come only from env or OS keyring, referenced by name (`api_key_env: ANTHROPIC_API_KEY`).
- Keys never go in run DBs, saves, blobs, exports, or logs. A redaction filter covers `sk-…`, `Authorization` headers, and URL credentials, and a CI test greps save fixtures for key patterns.
- Live evals run only from a manual `workflow_dispatch` job bound to a GitHub **Environment** (`live-evals`, required reviewer, environment-scoped secret, small Console spend limit). They never run on PRs from forks.
- Default CI uses mock and rule providers only.
- Cloud sessions can hold an API key via cloud-environment "API credentials" kept outside the sandbox ([cloud docs](https://code.claude.com/docs/en/claude-code-on-the-web)).

### Model-profile config example (`profiles/*.toml`)

```toml
[profile.sonnet-research]
provider = "anthropic"
model = "claude-sonnet-5-5"        # seen on models overview 2026-10-04; verify at implementation
api_key_env = "ANTHROPIC_API_KEY"
structured = "native_json_schema"
max_output_tokens = 1200
temperature = 1.0
timeout_s = 90
cache_prefix = true                # cache_control on stable prefix, ttl 5m
price = { input = 2.0, output = 10.0, cache_read = 0.2, cache_write_5m = 2.5, per = "MTok", source = "platform.claude.com/docs/en/about-claude/pricing", as_of = "2026-10-04" }

[profile.ollama-laptop-qwen8b]
provider = "openai_compat"
base_url = "http://127.0.0.1:11434/v1"
model = "qwen3:8b"
structured = "response_format_json_schema"
concurrency_group = "laptop-gpu"
max_output_tokens = 800
timeout_s = 180
price = { unknown = true }

[budget]
per_call_usd = 0.10
per_civ_usd = 5.0
per_run_usd = 10.0
allow_unpriced = true              # local only
```

## 7. Prior art: lessons

- **Generative Agents** ([arXiv 2304.03442](https://arxiv.org/abs/2304.03442)): 25 agents on gpt-3.5-turbo. The memory stream plus reflection plus retrieval scored on recency, importance, and relevance is the model for our belief/memory retrieval (FTS5). The cost lesson is to make cognition sparse: call per decision, not per tick.
- **Project Sid / PIANO** ([arXiv 2411.00114](https://arxiv.org/abs/2411.00114)): 10–1,000+ agents on GPT-4o. Without a coherence bottleneck, "agents say one thing but actually do something else". Our analogue is a single typed `ActionProposal` per civ per round, with speech and actions in one reply. They report that only the newest base model worked, so expect a qualification gap for small local models.
- **AgentSociety** ([arXiv 2502.08691](https://arxiv.org/abs/2502.08691)): over 10k agents. LLM calls are the bottleneck. Mitigations: local models, response caching, and LLM-only-for-complex-decisions. This supports our rule baseline plus selective cognition.
- **Concordia** ([repo](https://github.com/google-deepmind/concordia), [arXiv 2312.03664](https://arxiv.org/abs/2312.03664)): the Game Master pattern, where agents propose and the engine adjudicates, matches our authoritative sim.
- **CivRealm** ([arXiv 2401.10568](https://arxiv.org/abs/2401.10568)): LLM agents struggle in a full Civilization game. Hierarchical national-level advisers helped. Supports civ-level leaders over per-person LLM calls.

## ADR-0005: Model provider layer

**Status:** Proposed.

**Context:** Need many providers, a different model per civ, research-grade fairness and replay, no-credential default CI, open-source release, and a cloud-first dev setup without GPUs. Subscription OAuth is not a sanctioned route for in-game calls (§1). LiteLLM had a 2026 PyPI compromise.

**Decision:**
- An in-house `Provider` Protocol, with adapters Mock, Rule, Recorded, Anthropic (official SDK), and OpenAI-compatible (httpx; covers Ollama, llama.cpp, OpenRouter, vLLM). Gemini comes later.
- LiteLLM is an optional, hash-pinned extra only.
- Native structured output per route, plus local Pydantic and sim validation, plus at most 1 schema-repair retry. Invalid output becomes a recorded `no_action`.
- Named TOML model profiles with prices, `as_of`, and caps. Reserve-then-reconcile metering, fail-closed caps, no silent fallback, and model identity recorded per decision.
- Cognition requires a Console API key, OpenRouter key, or local endpoint. Never claude.ai OAuth.
- Live evals run only in a gated GitHub Environment.

**Consequences:**
- We maintain about 3 small adapters and track API changes ourselves.
- CI is free and deterministic.
- Players pay their own providers.
- The subscription funds development only.
- Qualification results gate which models are "research-grade".

**Revisit if:** Anthropic publishes a sanctioned subscription route for personal Agent SDK apps, or we need more than 5 provider wire formats.
