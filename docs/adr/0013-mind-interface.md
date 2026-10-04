# ADR-0013: The mind interface: places, standing policy, uniform orders, journal

- **Status:** Proposed
- **Date:** 2026-10-04
- **Deciders:** creator (proposed by the planning review)
- **Amends:** ADR-0005 (proposal schema), ADR-0008 (how the action list is presented to models)
- **Research:** [`80-plan-review-2026-10-04.md`](../research/80-plan-review-2026-10-04.md)

## Context
A **mind** is one model-driven decision maker. A **council** is one decision turn: the mind is shown an observation and replies. The first-slice design (research note 50) gives the mind tile coordinates, entity ids and a flat record of 13 action kinds. The review found:

- **Models handle raw grids badly.** Accuracy on text grids fell 42.7% on average as grids grew. Harnesses that worked gave named places and digested context.
- **Models do not carry out their own plans reliably.** In a Civilization VI benchmark, agents executed 48% to 66% of their stated commitments within ten turns.
- **Long runs fail through loops, not full memory.** In Vending-Bench, failure was unrelated to the context filling up, and a larger memory did worse.
- **Reply formats have hard limits.** Claude's structured output allows 24 optional and 16 union-typed parameters per request. Small local models and some OpenRouter endpoints are stricter still.

## Decision

### 1. Places
- World generation partitions the map into named **places**: `Place{place_id, kind, tiles, centroid, neighbours}`. Target 12 to 30 places on a 64 by 64 map.
- The partition function is chosen per scenario: `grid_blocks` for the petri dish, `terrain_regions` from M1.
- Models never see tile coordinates. Orders name a place (`"PL07"`). Rules turn that into movement, worker assignment and paths.
- A civilization may give a place its own name. Names are text and never touch physics.

### 2. The observation (contract `m0`, grows by milestone)
Rendered from a typed object, in this order:

| Section | Content |
|---|---|
| `calendar` | tick, season, year, council number, ticks until the next scheduled council |
| `status` | population, food in person-days, stores; each with its change since the last council |
| `places` | every known place: id, name, kind, travel time, what was seen there and when |
| `events` | evidence since the last council, at most 20 items, each with id, time, place and witnesses |
| `messages` | quoted text, with who delivered it and how it reached the council |
| `standing` | the current policy, open tasks, and each commitment as met, pending or missed |
| `last_results` | every order from the previous council with its outcome and reason code |
| `knowledge` | accessible claims and recorded beliefs (from M3) |
| `journal` | the mind's own text from its previous reply |

The status summary is pushed every council. Critical state is never something the mind has to ask for. Hidden causes, other civilizations' private data and unseen truth stay structurally absent (existing invariant).

### 3. The reply
One JSON object. Every field is required. An empty string, zero or an empty list means "not used". There are **no optional and no union-typed fields**, so the same schema works on every provider.

```json
{
  "decision_id": "…",
  "policy": {"allocations": [{"activity": "FORAGE", "place": "PL07", "share": 600}], "ration": 1000},
  "orders": [{"kind": "SCOUT", "place": "PL11", "target": "", "qty": 2, "text": ""}],
  "messages": [{"to": "VOICE", "text": "…"}],
  "commitments": [{"kind": "STOCK_AT_LEAST", "place": "", "qty": 400, "by_council": 9}],
  "beliefs": [{"statement": "…", "evidence": ["EV0450"]}],
  "names": [{"id": "PL07", "name": "…"}],
  "journal": "…",
  "annal": "…"
}
```

- **`policy`** is standing. It stays in force until replaced. Shares are permille and sum to at most 1000.
- **`orders`** are one-off tasks, at most 8. Every order has the same five fields.
- **`messages`**, at most 3. `to` is another civilization's id or `VOICE` (ADR-0017).
- **`commitments`**, at most 3, are typed promises the simulation can check.
- **`beliefs`**, at most 3, must cite evidence ids present in the observation.
- **`journal`**, at most 1,200 characters, replaces the previous journal. **`annal`**, at most 200 characters, is the line for the chronicle.
- Over-long text is cut at the limit and flagged `TEXT_TRUNCATED`. It is not a rejection.

### 4. Vocabulary by milestone
| Milestone | Order kinds added | Commitment kinds added |
|---|---|---|
| M0 | `FORAGE`, `MOVE_CAMP`, `SCOUT` | `STOCK_AT_LEAST`, `BE_AT` |
| M1 | `STORE`, `BUILD`, `PLANT`, `ASSEMBLE` | `HAVE_BUILT` |
| M2 | `SEND_ENVOY`, `GIVE`, `OFFER_TRADE`, `RAID`, `DEFEND` | `NOT_ATTACK`, `DELIVER` |
| M3 | `TEACH`, `RECORD` | — |
| M5 | `EXPERIMENT` | — |
| M6+ | rule primitives, see ADR-0019 | — |

`ASSEMBLE` gathers people at a place for a stated purpose and may consume goods. The purpose is free text. The engine attaches no meaning to it.

The 13 actions of ADR-0008 map onto these kinds. Their validation rules and rejection reasons in research note 50 section 3 still apply.

### 5. Validation
Schema, then civilization and decision id, then observation version, then each order against cumulative reservations. Invalid orders are dropped with a reason; valid ones commit. An invalid policy leaves the previous policy in force. Model output never changes state except through this path.

### 6. Continuity
- The journal is part of civilization state and is hashed. It is the mind's only self-written memory and it is bounded on purpose.
- Commitments give a measurable **intent-execution rate**: the share met by their due council.
- A mind that returns the same policy and orders for five councils while its status changed is marked `STALLED` in the metrics. Nothing is substituted.

### 7. Prompts
- The system prompt is fixed per contract version and neutral (ADR-0019): what the mind stands for, what it can perceive, the reply format. No persona, no hints about institutions.
- The trait numbers in ADR-0008 (risk aversion, aggression and so on) configure **rule baselines only**. Giving them to a model is a declared experimental treatment, not a default.
- Speech and visions appear as quoted data in `messages` or `events`, never in the system prompt (existing invariant).

### 8. Outcomes and versions
- Every decision ends in exactly one category: `VALID`, `PARTIAL`, `INVALID`, `REFUSAL`, `TRUNCATED`, `TIMEOUT`, `PROVIDER_ERROR`, `BUDGET`.
- The contract has a version (`m0`, `m1`, …). A milestone may add order kinds and sections. Every recorded decision stores its contract version, and schemas live in `schema/`.

## Alternatives considered
- **The flat 13-action record** (ADR-0005). It nears the provider limits already, and later levels add 14 more kinds.
- **Raw tile grids or coordinate lists.** Against the evidence, though M0 measures the difference as an experiment.
- **An unbounded memory log with retrieval.** Against the Vending-Bench result, and harder to hash and replay.
- **One model call per person.** Rejected in research note 70 on cost and coherence.

## Consequences
- Path-finding, worker assignment and task execution are rule code. The mind steers; it does not micromanage.
- Place generation becomes part of world generation and of the state hash.
- The M0 experiment compares place-based and grid-based observations, so a `grid` renderer exists for that experiment only.
- Revisit if qualification shows models cannot express what they need through uniform orders.

## References
- CivBench (arXiv 2609.02459); Vending-Bench (arXiv 2502.15840); "Stuck in the Matrix" (arXiv 2510.20198); "Democratizing Diplomacy" (arXiv 2508.07485).
- Claude structured outputs documentation (limits on optional and union-typed parameters).
