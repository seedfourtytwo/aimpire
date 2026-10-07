# E0 pre-registration: can a model-driven mind keep a group fed?

- **Status:** pre-registered, not yet run. Merged before any live run (ADR-0014 section 5).
- **Date:** 2026-10-04
- **Milestone:** M0e (backlog). **ADRs:** 0013, 0014, 0018, 0019.
- **Batch files:** `experiments/e0-dry-run.yaml` (free, CI), `e0-ollama-pilot.yaml`,
  `e0-ollama.yaml`, `e0-haiku-primary.yaml`, `e0-haiku-check.yaml`, `e0-openrouter.yaml`.
- **Integrity:** every batch file names this document. `aimpire batch` stores its BLAKE2b-256
  hash in every run manifest, beside the batch file's own hash. `aimpire batch <file> --verify`
  lists every run made from another version of either, so an edit after the runs is visible.

Nothing in this document may change once the first live run of E0 exists. A change before
then is a new commit of this file, and runs made before it are not used.

## 1. The question

One group of 30 people lives on the M0 petri dish: a 64 × 64 map in 16 places, one wild
food that regrows logistically, no births. Each council (every 10 days) a mind sets who
forages where, whom to send scouting, and the ration. **Can a model-driven mind keep the
group fed for two years, and how does it compare with the four rule baselines on the same
worlds?**

The baselines (`cognition/m0_baselines.py`) and their behaviour over 200 worlds are in the
[M0 reference bands](m0-reference.md):

- `rule:random`: random shares of all the people over the known places;
- `rule:greedy`: everyone but one scout on the place with the most food seen;
- `rule:half_full`: forage a place only above half its estimated ceiling, and only the surplus;
- `rule:msy`: hold each place at the analytic optimum of the disclosed regrowth rule.

## 2. Arms

All arms are knowledge arm **A0** (ADR-0018: a pretrained model, familiar world). The two
factors come from the roadmap row for M0:

| arm id | renderer | regrowth rule | what the mind is shown |
|---|---|---|---|
| `places-hidden` | places | hidden | the base system prompt; known places as a list (primary condition) |
| `places-disclosed` | places | disclosed | the same, plus the rule text below |
| `grid-hidden` | grid | hidden | the same facts laid out on the block grid |
| `grid-disclosed` | grid | disclosed | the grid, plus the rule text |
| `baselines` | places | hidden | the four rule baselines (they read the typed observation; the text is unused) |

**Known property of the grid arms (accepted by the creator, 2026-10-06).** The grid renderer draws every place, with unseen ones as `?`, so a mind in a grid arm can count how many places the map has. The places arms do not show this. It is accepted for E0 and stated here so H4 is read with it in mind; a grid that hides the count is a later change.

**The disclosed rule** is appended to the system prompt by `cognition.disclosed.disclosure_text`
from the rules data, so it is exactly what the baselines know: the regrowth rule with its two
numbers, a person's daily need, and how much a worker brings home from a place `d` days away.
It says nothing about any one world (no ceiling, no fertility, no stock), names no target and
no strategy, and passes the ADR-0019 word check. With rules v1 it reads:

```text
How food works here (the same at every place):
- Wild food at a place grows back each day by r * F * (K - F) / K + s * (K - F), where F is the food there now and K is the most that place can hold. r = 0.08 and s = 0.001 a day. K differs from place to place and is not told to you.
- One person eats 1 unit of food a day on a full ration.
- One worker gathering at a place d days away brings home 10 / (1 + 2 * d) units a day, while that much food is there.
```

"Hidden" sends the base system prompt unchanged. The observation is the same in both; the
prompt hash of each arm is in every run manifest.

**Later, not in E0: arm A2.** In M0 the place names are already neutral ids (`PL07`), so the
familiar part is the scenario itself: harvesting a renewable stock is a textbook problem with
a textbook answer (hold the stock near half its ceiling). An A2 version needs per-seed
ecology (regrowth rate, seed term and ceilings drawn within tested ranges, ADR-0018 section 3)
and coined names for the food, which arrive with M1 and M5. It is planned as E0b, with its own
pre-registration. Until then any E0 result is labelled A0, "possibly recalled" in the sense of
ADR-0019 section 6.

## 3. Models

| file | model | profile | why |
|---|---|---|---|
| `e0-ollama-pilot.yaml`, `e0-ollama.yaml` | qwen3:8b with an 8,192-token context, local | `profiles/ollama-8k.toml` (model built from `profiles/qwen3-8b-8k.Modelfile`) | open weights, free, anyone can re-run (ADR-0014 section 6); the full grid of arms (section 3) |
| `e0-haiku-primary.yaml` | Claude Haiku 4.5 | `profiles/anthropic-haiku-4-5-e0.toml` | frontier model, primary condition (ADR-0014 section 3) |
| `e0-haiku-check.yaml` | Claude Haiku 4.5 | the same | the one check: rule disclosed |
| `e0-openrouter.yaml` (optional) | chosen before its first run | `profiles/openrouter-e0.toml`, made from the template | breadth: a second family at low cost |

The Ollama profile runs qwen3:8b with thinking off (`effort = "none"`, sent as
`reasoning_effort`). With thinking on, a council reply took a median 96 s and the model
failed `aimpire qualify` on JSON validity and latency; with it off, replies take about 6 s.
`aimpire qualify` still reports FAIL on order validity (26 %, mark 80 %, 2026-10-07): the model
allocates more workers than it has. The creator chose to run the pilot anyway as an
exploratory exception: it is free, and how the model fails is part of what E0 measures. The
thresholds and the prompt are unchanged. No live E0 run existed when this was written.

Model settings are pinned in the profiles; nothing is left to a provider default except where
a profile says so. The Haiku E0 profile differs from `anthropic-haiku-4-5.toml` only in its
planning limits (6,000 input and 2,048 output tokens a call; a council is estimated at about
3,000 input tokens from the measured prompt sizes). Every comparison of one model is finished inside one availability window
(ADR-0014 section 2).

## 4. Hypotheses

Metric for all five: `survival_ppm`, the people alive after 240 days as parts per million of
the 30 at the start. "Model" means the mind under test in the named arm; comparisons are
paired by seed.

| | hypothesis | direction | tested on |
|---|---|---|---|
| **H1** | the model keeps more people alive than `rule:random` | model > random | primary condition, every model |
| **H2** | the model keeps more people alive than `rule:greedy` | model > greedy | primary condition, every model |
| **H3** | the model keeps fewer people alive than `rule:half_full` | model < half full | primary condition, every model |
| **H4** | named places help: `places-hidden` keeps more alive than `grid-hidden` | places > grid | `e0-ollama` |
| **H5** | knowing the rule helps: `places-disclosed` keeps more alive than `places-hidden` | disclosed > hidden | `e0-ollama`; Haiku as a secondary analysis |

Why these directions. H1 and H2: a capable planner should at least avoid over-harvesting what
it can see. H3: the simple sustained rule kept all 30 people alive for five years on all 200
reference worlds, and the ADR-0013 evidence suggests models execute their own plans
imperfectly over many councils. H4: ADR-0013 cites a 42.7 % accuracy loss on text grids. H5: the rule removes
the need to learn regrowth from dated snapshots.

## 5. Metrics

- **Primary:** `survival_ppm` at day 240.
- **Secondary**, all reported, none confirmatory: `final_near_camp_mu` (wild food left on the
  camp's place and its neighbours: did it eat its own future?), `deaths`, `final_stores_mu`,
  `usable_share_ppm` (valid or partial replies), `refusal_share_ppm`, `failure_share_ppm`
  (truncated, timeout, provider error, budget). Every decision's outcome is counted; failures
  are never replaced (ADR-0013 section 8). A failed council leaves the standing policy in
  force; at the first council there is none, so a mind that never replies forages nothing
  (the dry run's mock shows this floor).
- **Bands:** population, deaths, stores and food near the camp at every season boundary, as
  10th percentile, median and 90th percentile over runs, beside the reference bands.

## 6. Analysis plan

- **Unit of analysis: the world seed** (ADR-0014). For each group (arm, mind) and seed, the
  value is the lower median of the metric over that seed's 3 replicates. Turns and replicates
  are never treated as independent.
- **Paired differences** per seed, model minus baseline (H1 to H3) or arm A minus arm B
  (H4, H5). `aimpire batch` writes them in the report's "Paired comparisons" section; H5 on
  Haiku pairs the two Haiku reports by seed by hand, with the same statistics.
- **Effect sizes:** the probability of superiority, P(A > B) + ½ P(tie), and the median
  paired difference with its exact 95 % interval from order statistics
  (`experiments.stats`). No normal approximation.
- **Test:** the exact one-sided sign test in the hypothesis's direction, ties dropped. With
  the arm order of the files, H4 reads `places-hidden` vs `grid-hidden` "A > B", and H5 reads
  `places-hidden` vs `places-disclosed` "A < B".
- **Multiplicity:** Holm–Bonferroni at α = 0.05 (one-sided) within each family: H1 to H3 per
  model; H4 and H5 together.
- **Decision rule.** A hypothesis is **supported** if its Holm-adjusted p is at most 0.05;
  **contradicted** if the one-sided p in the opposite direction is at most 0.05 (unadjusted);
  otherwise **inconclusive**. All three outcomes are reported with their effect sizes.
- **Ceiling.** Many seeds may tie at full survival. Ties are reported as such; they are not
  evidence for either direction. If every seed ties, the result is stated as "kept all 30
  alive on n of n seeds, as did the baseline".
- **Language:** rates under stated conditions ("kept at least 27 of 30 alive on 9 of 10 seeds
  with the rule hidden"), never traits (ADR-0014 section 5).

## 7. What would falsify each hypothesis

| | falsified (contradicted) if |
|---|---|
| H1 | the model keeps fewer alive than `rule:random`, one-sided sign p ≤ 0.05 |
| H2 | the model keeps fewer alive than `rule:greedy`, one-sided sign p ≤ 0.05: it over-harvests worse than taking everything in reach |
| H3 | the model keeps more alive than `rule:half_full`, one-sided sign p ≤ 0.05 |
| H4 | `grid-hidden` keeps more alive than `places-hidden`, one-sided sign p ≤ 0.05 |
| H5 | `places-hidden` keeps more alive than `places-disclosed`, one-sided sign p ≤ 0.05: the rule text hurts |

"Inconclusive" is not "falsified". Before adjustment, the one-sided sign test reaches
p ≤ 0.05 with 9 or 10 of 10 untied seeds in one direction, 8 of 9, or all of them when 5 to 8
seeds are untied; Holm's adjustment makes the first test of a family stricter.

## 8. Seeds, replicates and stopping

- **Confirmatory seeds:** 1001 to 1010, shared by every arm and file. They are disjoint from
  the calibration seeds (1 to 10, M0c) and the reference seeds (1 to 200), so nothing was tuned
  on them.
- **Pilot seeds:** 901 and 902 (`e0-ollama-pilot.yaml`), exploratory only, never pooled.
- **Replicates:** 3 per seed and arm (ADR-0014 minimum). Rule baselines are deterministic, so
  their replicates are identical; they run anyway, inside the same batch, for a self-contained
  report.
- **Horizon:** 240 days (two years), a council every 10 days: 24 councils a run. In the
  reference bands the baselines have separated by then and nothing changes after: at day 240
  the median survivors are 3 (`rule:random`), 8 (`rule:greedy`) and 30 (`rule:half_full`,
  `rule:msy`), and at day 600 they are 2, 8, 30 and 30. A longer horizon would cost more
  without separating the baselines further.
- **Sizing from the pilot** (ADR-0014 section 1): if, in the pilot, the replicates of any
  model arm on either seed differ in survival by more than 200,000 ppm (6 people), `e0-ollama`
  runs seeds 1001 to 1020 instead. That edit to `e0-ollama.yaml` is committed before its first
  run. The paid files stay at 10 seeds (budget).
- **No optional stopping.** Every planned run of a file is run; nobody looks at results to
  decide whether to continue.
- **Stops that are allowed**, each recorded in the report:
  - a budget refusal: the file is run unchanged in a later month;
  - infrastructure failure: if more than 20 % of a model's decisions in its first 3 runs end
    as `TIMEOUT` or `PROVIDER_ERROR`, stop, fix the setup (never the prompt or the design),
    and restart the file in a new runs folder; the aborted attempt is reported;
  - model retirement before a file is finished: restart that file with the replacement model
    as a new, separately labelled model, never pooled with the old.

## 9. Budget

Defaults: $20 a month across all runs, $2 a run (backlog F6). `aimpire batch` prints the
worst case before anything is called and refuses if it does not fit what is left.

| file | model runs × councils | worst case | realistic | machine time |
|---|---|---|---|---|
| `e0-dry-run.yaml` | 24 mock + 24 rule, × 4 | $0 | $0 | about 15 s |
| `e0-ollama-pilot.yaml` | 24 × 24 | $0 | $0 | 3 to 10 h at 20 to 60 s a council |
| `e0-ollama.yaml` | 120 × 24 | $0 | $0 | 16 to 48 h (twice that at 20 seeds) |
| `e0-haiku-primary.yaml` | 30 × 24 | $11.69 | about $4.70 | about 1 h |
| `e0-haiku-check.yaml` | 30 × 24 | $11.69 | about $4.70 | about 1 h |
| `e0-openrouter.yaml` | 30 × 24 | under $20 by choice of model | depends on the model | about 1 h |

- **Worst case** per Haiku call: 6,000 input tokens × $1/M + 2,048 output tokens × $5/M =
  $0.01624; per run, 24 calls = $0.39, under the profile's $1 run cap and the $2 default.
- **Realistic** per Haiku call: about 3,000 input and 700 output tokens = $0.0065; 720 calls
  per file = $4.68.
- **Order and months.** Month 1: dry run, pilot, `e0-ollama`, `e0-haiku-primary` (worst case
  $11.69). Month 2: `e0-haiku-check`, and `e0-openrouter` if wanted, each fitting what is left.
  The whole of E0 is expected to cost about $10 to $15 in total, under $20 in any month.

## 10. Exploratory versus confirmatory

**Confirmatory:** H1 to H3 on the primary condition of each model's confirmatory file
(`e0-ollama`, `e0-haiku-primary`, `e0-openrouter` if run), H1 and H2 on `e0-haiku-check`, and
H4 and H5 on `e0-ollama`, all on seeds 1001 to 1010 (or 1020) with the analysis of section 6.

**Exploratory**, reported and labelled as such, never used to support H1 to H5:

- the pilot, every secondary metric and every band;
- comparisons not listed above (for example `grid-disclosed` against anything);
- reading journals and annals: strategies a mind wrote down, anachronisms (ADR-0018 section 4),
  and every statement that it believes it is in a test or a game, counted per run
  (ADR-0014 section 4);
- the **recognition probe** (ADR-0014 section 4): before its confirmatory file, each model is
  asked once, outside the game, (a) what the situation in the system prompt and a council-1
  observation resembles, and (b) what the textbook way to keep these people fed would be. The
  answers are quoted in the report;
- any split, subgroup or metric thought of after the runs.

## 11. Report

The report follows [the E0 report template](e0-report-template.md): `aimpire batch` writes the
numbers, tables and charts (`runs/e0/<file id>/report.md`), and the write-up adds the decisions
of section 6, the deviations, if any, and the exploratory notes.
