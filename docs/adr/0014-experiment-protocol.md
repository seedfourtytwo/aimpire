# ADR-0014: Experiment protocol

- **Status:** Accepted (creator, 2026-10-04)
- **Date:** 2026-10-04
- **Deciders:** creator (proposed by the planning review)
- **Amends:** ADR-0005 (qualification and sampling assumptions)
- **Research:** [`80-plan-review-2026-10-04.md`](../research/80-plan-review-2026-10-04.md)

## Context
Aimpire's results are claims about how models behave. A 2025 review of 35 papers in this field found that most used a single run and none did sensitivity analysis. Long-horizon agent benchmarks report very high run-to-run variance and say plainly that 5 to 25 runs cannot rank models. Current provider facts also matter:

- Claude Opus 4.7 and later reject a non-default `temperature`, and the Messages API reference lists no seed parameter. Run-to-run variation cannot be configured away.
- Reasoning effort defaults differ between models, and thinking tokens count toward the output cap.
- Models are retired on 60 days' notice.

## Decision

### 1. Design
- **Unit of analysis:** the world seed. Models are compared by paired differences on shared seeds. Turns are never treated as independent.
- **Replicates:** at least 3 runs per model, seed and starting seat. Recorded replay proves a run can be audited; replicates show whether it would happen again.
- **Seats:** when several minds share a world, every model plays every seat.
- **Baselines:** random, greedy, a tuned heuristic, and the analytic optimum where one exists. Their scores are published beside the model scores.
- **Sample size:** tolerance bands for rule-baseline tests come from a reference ensemble of several hundred seeds. Model runs are sized from a pilot's variance, and the calculation is in the report.

### 2. Model configuration
- Each profile pins the model id and states reasoning effort and output cap explicitly. No setting is left to a provider default.
- `temperature` and `seed` are optional per provider. A profile may set them only where the provider accepts them.
- Each decision records tokens in, out and reasoning, latency, cost, the resolved model id and the call time.
- Every comparison is finished inside one model-availability window.

### 3. Robustness
- Two or three paraphrases of the prompt, two surface framings of the same mechanics, and shuffled order of options.
- The full grid of variants runs on open-weight models. Frontier models run the primary condition and one check.

### 4. What the mind knows
- Every run is labelled with its **knowledge arm** from ADR-0018 (`A0` familiar world, `A1` role-constrained, `A2` unfamiliar world, `A3` native mind).
- **Recognition probe:** outside the game, each model is asked what the scenario resembles and what the textbook strategy is. The answers go in the report.
- Every statement by a mind that it believes it is in a test or a game is counted.

### 5. Reporting
- **Pre-registration:** `docs/experiments/<id>/prereg.md`, or a single file `docs/experiments/<id>-preregistration.md` (as E0 uses; amended 2026-10-06), holds the hypothesis, the primary metric, seeds, models and budget. It is merged before the run.
- **Reference ensembles** (rule minds, one run per seed, `kind: reference`) are the one case where a condition may be run without model replicates; they describe the world, not a model (amended 2026-10-06).
- **One outcome per decision** (ADR-0013 categories), with all rates reported. Refusals are counted, never silently replaced.
- **Uncertainty:** distributions, medians and intervals from bootstrap or exact methods. No normal-approximation intervals on small samples.
- **Language:** rates under stated conditions ("raided in 4 of 20 worlds once food fell below 10 days"), never traits ("aggressive").
- **Emergence claims** follow the ledger rules in ADR-0019.

### 6. Durability
- Raw requests and responses are stored for every live call (ADR-0004 blob store) and are part of the published result.
- Every experiment keeps one open-weight arm that a third party can re-run.

## Alternatives considered
- **Single showcase runs.** Good for demos, worthless as evidence. Demos are labelled as demos.
- **Temperature zero with a fixed seed.** No longer available on the newest models and never fully deterministic.
- **Equalising reasoning budgets across providers.** There is no common unit; explicit settings plus cost reporting is the defensible option.

## Consequences
- Experiments cost more calls. Budgets in the roadmap assume open-weight models for iteration and frontier models for confirmation.
- The batch runner (F6) must support paired seeds, replicates, seat rotation and prompt variants from the start.
- Revisit thresholds after the first pilot.

## References
- Miller, "Adding Error Bars to Evals"; Bowyer et al., ICML 2025; Larooij and Törnberg 2025; Barrie and Törnberg 2025; CivBench 2026.
- Anthropic model deprecations page (sampling parameters and retirement notice).
