# Backlog: first issues

Work items for the foundation and the first milestone, in build order. Each becomes one GitHub issue, one branch and one pull request (see [`task-template.md`](../agents/task-template.md)).

**Tiers** (ADR-0016): **S** = strongest model, writes the acceptance tests and reviews. **I** = implementing model. **C** = creator only.

**Rule for every item:** the S-tier session writes the acceptance tests first, under `sim/tests/acceptance/`, marked as expected failures. The I-tier session makes them pass; the S-tier orchestrator (or the creator) then removes the mark, since acceptance files are protected (ADR-0022 amends ADR-0016 §3). It never edits the tests. If a test seems wrong, stop and report.

Verification for every item is `just check`, plus the named tests.

---

## G1 — Guard rails (before any feature work)

| Id | Tier | Work |
|---|---|---|
| G1a | C | Add the protected-path check to `ci.yml` (sketch below), create the GitHub environment `protected-change` with yourself as required reviewer, and add both jobs to `ci-ok.needs`. Confirm you are not on the `main` ruleset's bypass list. |
| G1b | S | `.claude/hooks/protect-paths.sh` and a `PreToolUse` hook on the Edit and Write tools in `.claude/settings.json`. The script exits 2 with a clear message when the target matches a protected path, unless `AIMPIRE_ALLOW_PROTECTED=1`. Add a `Stop` hook that lists protected files changed in the working tree. |
| G1c | S | `sim/tests/acceptance/README.md` (the read-only rule and the expected-failure convention). |
| G1d | C | Optional: a pull-request review workflow or routine pinned to a stronger model, using the checklist in [`review-checklist.md`](../agents/review-checklist.md). |
| G1e | C | Add an always-on `repo` job to `ci.yml` (sketch below) and to `ci-ok.needs`, so pull requests that touch only `tools/`, `.claude/` or docs also run `just check-repo` (ADR-0022). Until then it runs inside `check-sim`. |
| G1f | S | Split the two acceptance files listed in `tools/checks/hygiene-baseline.txt` below 500 lines, then delete their baseline entries. |

Protected paths: `sim/tests/acceptance/`, `fixtures/golden/`, `.github/`, `.claude/`, `docs/adr/`, `CLAUDE.md`, the config files `sim/ruff.toml`, `sim/pyrightconfig.json` and `sim/.importlinter`, and the repo gates `tools/checks/`, `ruff.toml` and `.pre-commit-config.yaml` (ADR-0022). They are kept out of `pyproject.toml` so that dependency changes stay unprotected.

Sketch for G1a (the creator adapts and pushes it; agents do not edit workflows):

```yaml
  protected-paths:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    permissions:
      contents: read
    outputs:
      touched: ${{ steps.diff.outputs.touched }}
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
          fetch-depth: 0
      - id: diff
        env:
          BASE: ${{ github.event.pull_request.base.sha }}
          HEAD: ${{ github.event.pull_request.head.sha }}
        run: |
          pattern='^(sim/tests/acceptance/|fixtures/golden/|\.github/|\.claude/|docs/adr/|CLAUDE\.md$|sim/ruff\.toml$|sim/pyrightconfig\.json$|sim/\.importlinter$|tools/checks/|ruff\.toml$|\.pre-commit-config\.yaml$)'
          if git diff --name-only "$BASE" "$HEAD" | grep -Eq "$pattern"; then
            echo "touched=true" >> "$GITHUB_OUTPUT"
          else
            echo "touched=false" >> "$GITHUB_OUTPUT"
          fi

  protected-approval:
    needs: protected-paths
    if: needs.protected-paths.outputs.touched == 'true'
    runs-on: ubuntu-latest
    environment: protected-change   # required reviewer: the creator
    permissions: {}
    steps:
      - run: echo "Protected paths changed and the creator approved."
```

Sketch for G1e (the creator adapts and pushes it):

```yaml
  repo:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7 # v10.2.0
      - run: uvx --from rust-just==1.58.0 just check-repo
```

---

## F1 — Bootstrap

**Tier:** S for the tests, I for the rest. **Depends on:** G1b, G1c. **ADRs:** 0003, 0006, 0016.

Files:

```
sim/pyproject.toml          name "aimpire"; requires-python ">=3.14,<3.15"
                            deps: numpy, pydantic (v2)
                            dev: pytest, hypothesis, ruff, pyright, import-linter
sim/.python-version         3.14
sim/uv.lock                 committed; CI uses `uv sync --locked`
sim/src/aimpire/__init__.py                 __version__
sim/src/aimpire/{sim,cognition,persistence,contracts,api,cli}/__init__.py
sim/src/aimpire/cli/main.py                 entry points `aimpire` and `aim`; `--version`
sim/tests/unit/test_smoke.py
justfile                    lint, fmt, typecheck, test, test-fast, check-sim; `check` runs check-sim
```

Configuration that must exist:

- **Import rules** (import-linter): `aimpire.sim` may not import `aimpire.cognition`, `aimpire.persistence`, `aimpire.api` or `aimpire.cli`.
- **Banned APIs** (ruff) inside `aimpire.sim`: `random`, `time.time`, `time.monotonic`, `datetime.datetime.now`, `datetime.date.today`, `numpy.random`.
- **pyright** strict on `aimpire.sim`, basic elsewhere.

Acceptance tests: `test_cli_version`, `test_import_rules_configured`, `test_banned_apis_configured`, `test_package_layout`.

Out of scope: any simulation logic, any dependency not listed. Verify every version against PyPI before pinning.

---

## F2 — Deterministic core

**Depends on:** F1. **ADRs:** 0007, 0011, 0012. Five small pull requests, in this order.

### F2a — `aimpire/sim/fixed.py`
Interfaces exactly as in ADR-0012 section A: `PPM`, `apply_rate`, `chance_ppm`, `stochastic_round`, and `apply_rate_array` for numpy `int64` layers.

Acceptance tests:

- `test_apply_rate_matches_exact_fraction`: over 10,000 ticks the summed deltas equal the floor of the exact total.
- `test_apply_rate_never_stalls`: 1,000 ppm per tick from 5,000 reaches zero.
- `test_slow_rate_accumulates`: 10,000 ppm per year on a value held at 1,000 units yields exactly 10 units over 120 ticks.
- `test_stochastic_round_is_unbiased`, `test_chance_ppm_frequency`: within binomial bounds over 100,000 draws.
- `test_negative_input_rejected`, `test_array_overflow_raises`.

### F2b — `aimpire/sim/rng.py`
Interfaces exactly as in ADR-0012 section B: `Stream` enum with the fixed numbers, `stream_key`, `mix64`, `draw`, `draw_array`, `uniform_int`, `permutation`.

Acceptance tests:

- `test_known_answer_vectors`: the eight rows of the ADR table.
- `test_array_equals_scalar`: 5,000 ids including values above 2**40.
- `test_uniformity_smoke`: chi-square over 100 buckets across ids, ticks, streams and `n` below 160; correlations below 0.01.
- `test_stream_numbers_frozen`, `test_permutation_complete_and_deterministic`.

### F2c — `aimpire/sim/calendar.py`
`Calendar(ticks_per_season, seasons_per_year)` with `ticks_per_year`, `season_of(tick)`, `year_of(tick)`, `is_season_start(tick)`, `is_year_start(tick)`. `Rate(ppm, per)` with `per in {"tick", "season", "year"}` and `Rate.resolve(calendar) -> (ppm, per_ticks)`. A loader for `rules/v1/calendar.yaml`.

Acceptance tests: `test_default_calendar_is_120_ticks`, `test_rate_resolution`, `test_calendar_loaded_from_rules`.

### F2d — `aimpire/sim/ids.py`, `state.py`, `hashing.py`
`IdAllocator` (monotonic, in state). `WorldState` holding tick, id counter, named `int64` layers, entities by id, carries. `state_hash(state)` and `subsystem_hashes(state)` as ADR-0007, carries included.

Acceptance tests:

- `test_hash_stable_across_processes`: two fresh interpreters, same hash.
- `test_hash_ignores_insertion_order`, `test_hash_changes_with_any_field`.
- `test_float_in_state_rejected`.

### F2e — `aimpire/sim/scheduler.py`
A `System` protocol: `name`, `cadence` (`tick | season | year`), `sequential`, `step(state, ctx)`. A `Scheduler` built from a preset: an ordered list of system names with parameters. `ctx` gives the calendar, `stream_key` access and the acting order for sequential systems.

Acceptance tests:

- `test_empty_world_same_hash_after_360_ticks` for two runs with one seed, and a different hash for another seed once a drawing system is present.
- `test_cadence_runs_on_boundaries`.
- `test_preset_mismatch_raises`: a missing or unknown system is an error, never a silent skip.
- `test_sequential_order_changes_each_tick_and_replays`.

---

## F3 — Ledger and invariants

**Depends on:** F2. `aimpire/sim/ledger.py`: every change to a conserved quantity is recorded with tick, material, delta, kind and reference. An invariant runner checks after each system in debug mode.

Acceptance tests: `test_ledger_balances_toy_system`, `test_unrecorded_change_detected`, `test_negative_stock_raises`, `test_carry_included_in_balance`.

---

## F4 — Watch (parallel with F5)

**Depends on:** F3.

| Id | Work | Acceptance |
|---|---|---|
| F4a | Metrics time series per run; dot frames as arrays rendered to PNG | `test_frame_array_hash_stable` (hash the array, not the PNG) |
| F4b | Replay export (one JSON file per run) and a static Canvas2D player under `client/replay/` | `test_replay_roundtrip`; the player opens the fixture replay |
| F4c | A Markdown lab notebook per run: config, seed, charts, metrics, outcome counts | `test_notebook_lists_required_sections` |

Charts follow the Tufte rules in `CLAUDE.md`. Verify any new dependency version before adding it.

---

## F5 — Mind interface v0 (parallel with F4)

**Depends on:** F3. **ADRs:** 0004, 0005, 0013.

| Id | Work | Acceptance |
|---|---|---|
| F5a | `contracts/mind.py`: Pydantic `Observation` and `MindReply` for contract `m0`; schema exported to `schema/`; `just schema-check` | `test_reply_schema_has_no_optional_or_union_fields`; `test_schema_export_is_current` |
| F5b | `cognition/provider.py`: the `Provider` protocol; `MockProvider`, `RuleProvider`, `RecordedProvider` | `test_recorded_provider_replays_exactly` |
| F5c | `sim/places.py` with `grid_blocks`; `cognition/observe.py` builder; `cognition/render.py` with the `places` and `grid` renderers | `test_observation_excludes_hidden_fields`; `test_other_group_state_does_not_change_observation_hash` |
| F5d | `sim/actions/validate.py`; decision log with the eight outcome categories | `test_invalid_reply_changes_nothing`; `test_partial_acceptance`; `test_stale_observation_rejected`; `test_duplicate_decision_is_idempotent` |
| F5e | Council barrier, budgets, run store (SQLite manifest, inputs, decisions, checkpoints) | `test_recorded_replay_matches_every_checkpoint_hash`; `test_budget_refuses_over_cap` |

No network in any of this. `RuleProvider` returns ordinary replies through the same validator.

---

## F6 — Live adapters and batch runner

**Depends on:** F5. **ADRs:** 0005, 0009, 0014.

| Id | Work |
|---|---|
| F6a | `OpenAICompatProvider` (httpx): Ollama, llama.cpp, OpenRouter. Structured output by JSON schema. |
| F6b | `AnthropicProvider` (official SDK). Verify the current API against the documentation first. |
| F6c | `aimpire qualify <profile>`: frozen observations, reports schema adherence, order validity, latency, tokens, cost. |
| F6d | `aimpire batch`: paired seeds, replicates, seat rotation, prompt variants; one report per experiment. |

Live calls run only from an explicit profile with a budget. CI never calls a provider.

### Budget rules (creator decision, 2026-10-04)

- **Monthly cap: 20 dollars in total** across OpenRouter and Anthropic. Ollama runs locally and costs nothing.
- **Two layers of protection.** The creator sets a hard monthly limit on each provider's dashboard. The code also keeps its own spend ledger in the run store and refuses a call that would cross a cap (`test_budget_refuses_over_cap`).
- **Code defaults:** 20 dollars a month across all runs; 2 dollars per run unless the profile sets less; every profile names its price per million input and output tokens, checked against the provider's current price page.
- **Estimate before spending.** `aimpire batch` and `aimpire qualify` print the worst-case cost (councils × tokens × price) and refuse to start if it exceeds the remaining budget.
- **Order of use:** mock, rule and recorded providers first; Ollama for iteration; OpenRouter cheap models for breadth; Anthropic for selected runs.
- **Keys:** `OPENROUTER_API_KEY` and `ANTHROPIC_API_KEY`, read from the environment by name (profiles hold only `api_key_env`). In GitHub they live only in the gated `live-eval` environment.

---

## M0 — Petri dish (specified 2026-10-04)

**Goal.** One tribe on a flat map with one regrowing food. Rule baselines show the physics behave as theory predicts; then a mind is scored against them. **ADRs:** 0007, 0010, 0011, 0012, 0013, 0014, 0015, 0019, 0020 (W0 rates).

**Rules data** (`rules/v1/m0.yaml`, a rules version bump, its own PR): map size (default 64 × 64 tiles), place block (16 → 16 places), food ceiling per tile at Earth (milli-units), fertility noise range, regrowth rate and seed term (each with its period, ADR-0011), daily food need per person, spoilage of stores, starvation death chance, scout sight, starting people and stores. No numbers are hard-coded in `sim/`.

**Physics from W0.** The plant ceiling, walking speed (travel ticks), carry load and walking energy come from the derived rates, so the Lab knobs reach M0.

| Id | Work | Acceptance (tests written first) |
|---|---|---|
| M0a | `sim/systems/regrowth.py` and `sim/world/m0.py`: worldgen from the seed (WORLDGEN stream; fertility as integer value noise), a `food` layer in milli-units, per-tile ceiling = W0 plant ceiling × fertility. Logistic regrowth with a seed term, ΔF = r·F·(K−F)/K + s·(K−F), through `fixed.apply_rate` with carries; ledger kind `REGROWTH`. Preset `m0` registered. | `test_empty_map_settles_at_ceiling` (every tile within 1 % of K after the predicted time); `test_regrowth_matches_closed_form` (one tile against the exact discrete recurrence); `test_constant_harvest_sweep_peaks_near_half_full` (a harvest-fraction sweep on rule code peaks where theory says, within a stated tolerance); `test_ledger_balances_every_tick`; `test_gravity_changes_ceiling_only_through_w0` |
| M0b | `sim/systems/forage.py`, `camp.py`, `scout.py`, `hunger.py`; the commit step turns the standing policy into work. Each tick: <ul><li>foragers at a place gather min(carry per trip ÷ (1 + 2·travel ticks), food available), taking from the place's tiles in proportion to their food (amended in M0c: emptied tiles barely regrow, so tile-by-tile harvesting starved every tribe) (`HARVEST`, tile → stores);</li><li>walking energy is eaten from stores (`CONSUME`);</li><li>people eat the ration (`CONSUME`), and stores spoil (`SPOIL`);</li><li>a shortfall gives each person a death chance from the LIFE stream;</li><li>`MOVE_CAMP` takes the travel ticks, with no foraging meanwhile;</li><li>`SCOUT` writes `evidence` and updates `known` with a dated snapshot.</li></ul> Population is a count on the `civ` entity; there are no births in M0 (they come in M3). Every change is written into the `civ` / `evidence` / `message` layout read by `civ_record.py`. | `test_foraging_conserves_food`; `test_no_food_means_deaths_and_no_negative_stores`; `test_move_camp_takes_travel_time`; `test_scout_reveals_snapshot_not_live_truth`; `test_unknown_place_order_rejected_without_leak`; `test_turn_order_independent` |
| M0c | Rule baselines as `RuleProvider` policies: `random`, `greedy` (all workers on the richest known place), `half_full` (forage a place only above K/2, effort scaled to hold it there), `msy` (the analytic optimum for the disclosed rule). `aimpire run m0 --mind rule:half_full --seed 1 --ticks N --out runs/` writes the run store, the replay file and the lab notebook. | `test_half_full_outlives_greedy_on_most_seeds` (k of n, stated in the test); `test_run_cli_is_reproducible` (same hashes twice) |
| M0d | `aimpire batch` ensemble of the baselines over several hundred seeds; reference bands (median and 10–90 %) of population, stores and stock at fixed checkpoints, written to `docs/experiments/m0-reference.md` with charts | `test_reference_bands_reproduce` (a 10-seed subset) |
| M0e | Experiment E0: pre-registration file (hypotheses, metrics, arms: places or grid, rule disclosed or hidden, knowledge arm A0), the batch file, and a report template. Runs with rule and mock minds in CI; live arms run by hand under the budget | pre-registration hash stored in every run manifest |

**Lab steps landing alongside:** W0 and LAB0 before M0a; LAB1 (`aimpire lab twin`) after M0c.

---|---|
| M0a | Flat map, one food layer, regrowth with a seed term, `grid_blocks` places |
| M0b | People with energy; rule execution of `FORAGE`, `MOVE_CAMP`, `SCOUT`; starvation |
| M0c | Baselines: random, greedy, and the harvest policy that holds stock near half full |
| M0d | Ensemble validation: the reference bands from several hundred seeds |
| M0e | Experiment E0: pre-registration, run, report |

---

## Lab track (ADR-0020, proposed; outline)

| Id | Work | Acceptance |
|---|---|---|
| W0 | `rules/v1/world.yaml` (gravity, sunlight, rain, tilt in ppm or milli-degrees); `aimpire.rules.physics` integer laws: walk ∝ √g, carry ∝ 1/g, walk energy ∝ g, water ∝ √g, tree ∝ g^(−1/3), fall ∝ g, throw ∝ 1/g, season from tilt, growth ceiling = min(sunlight, water) | `test_earth_constants_are_identity`; `test_laws_are_monotonic` (Hypothesis); `test_derivation_uses_no_floats`; `test_beyond_validated_range_is_flagged` |
| LAB0 | `aimpire.lab.knobs` registry and schema export; `--set path=value`; overrides in the manifest and rules hash | `test_unknown_knob_refused`; `test_out_of_allowed_range_refused`; `test_world_override_changes_rules_hash`; `test_mind_override_does_not`; `test_no_outcome_knobs` (name lint) |
| LAB1 | `aimpire lab twin`: paired seeds; first divergence tick and part; small-multiple report | `test_twin_with_no_override_never_diverges` |
| LAB2 | `aimpire lab sweep`: 1-D and 2-D; free providers by default | `test_sweep_is_reproducible` |
| LAB3 | forks from checkpoints; world events as recorded data | `test_fork_replays_exactly` |
| LAB4 | workshop page in the web console | — |

---

## Native mind track (ADR-0021, proposed; outline)
Starts after M0b. Never blocks a milestone. Training code lives in `native/`, outside CI.

| Id | Work | Acceptance |
|---|---|---|
| N0 | `native/vocab/v1.txt` closed vocabulary and checker script | `test_checker_refuses_out_of_vocabulary_line`; the list contains no tool, office, worship, money, writing or farming words |
| N1 | Deterministic corpus generator: primer templates, narrated rule-baseline runs, council examples | `test_corpus_is_reproducible_from_seed`; `test_every_line_passes_vocabulary` |
| N2 | Tokenizer and small decoder-only training script (PyTorch); model card; GGUF export | manual: loss curve and sample text in the model card |
| N3 | Reply grammar (GBNF) generated from the m0 contract; a llama.cpp/Ollama profile | `test_grammar_accepts_only_valid_replies` |
| N4 | `aimpire qualify` on the native mind; M0 experiment arm A3 | pre-registered report |
| N5 | Generations: fine-tune on its own chronicles | later |
