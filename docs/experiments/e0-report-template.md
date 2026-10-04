# E0 report template

Copy this page to `docs/experiments/e0-report.md` when the confirmatory runs are done, and
fill it in. Numbers come from the batch reports (`runs/e0/<file id>/report.md` and
`report.json`); this page adds the decisions and the reading. Keep it separate from the
[pre-registration](e0-preregistration.md), whose hash is in every run manifest and must not
change.

## 1. What was run

- Files, their hashes and the pre-registration hash, as printed at the top of each batch report.
- `aimpire batch <file> --verify` output for each file (it must say the file matches every run).
- Models: profile, resolved model id, call dates, availability window.
- Seeds actually used (10 or 20 for `e0-ollama`, with the pilot numbers that decided it).
- Spend: charged per file (the batch reports' run table), against the worst case.

## 2. Deviations

Every difference from the pre-registration, with its reason: aborted attempts, budget
refusals, a model swap. "None" if none.

## 3. Confirmatory results

One row per hypothesis and model, from the "Paired comparisons" tables:

| hypothesis | model | seeds | A more / same / B more | median difference [95 % interval] | superiority | one-sided p | Holm p | decision |
|---|---|---|---|---|---|---|---|---|
| H1 | | | | | | | | supported / contradicted / inconclusive |

Then one sentence per hypothesis, as a rate under conditions, for example: "With named places
and the rule hidden, qwen3:8b kept at least 27 of 30 people alive on 7 of 10 worlds over two
years; `rule:greedy` did on 0 of 10."

## 4. Bands

The batch report's band charts beside the [M0 reference bands](m0-reference.md), with one
paragraph on where each model's median sits relative to the baselines.

## 5. Exploratory

Labelled as exploratory throughout:

- secondary metrics, pilot results;
- what the minds wrote in their journals about their own plans, quoted;
- statements that the mind believes it is in a test or a game, counted per run;
- the recognition probe answers, quoted;
- anything noticed after the runs.

## 6. What this means for M1

Two or three sentences. Claims stay inside A0 (ADR-0018): a parallel with textbook harvesting
is "possibly recalled", never "emergent".
