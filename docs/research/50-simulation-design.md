# Great Filter — First-Slice Simulation Design

Status: draft from planning agent, 2026-10-04. Scope: 64×64 map, 2 civilizations × 30 people. All rules are versioned as `rules/v1`. Items marked *[ext]* are extension points: named, not built.

## 0. Determinism foundations
- **Integers only in state.** Quantities in milli-units (`1 food unit = 1 person-day = 1000 mu`). Rates/probabilities in permille (‰) or ppm. Floats never stored or hashed.
- **Counter-based RNG:** `draw(seed, tick, stream, entity_id, n) = blake2b(...) → u64`. Streams: `weather, growth, spoil, combat, teach, experiment, fire, worldgen, baseline`. No draw depends on the order of other draws, so adding a subsystem never shifts existing results.
- **Hashing:** canonical JSON (sorted keys, ints/strings only, entities by id) → blake2b-256. Rolling hash each tick; full snapshot hash at each cognition barrier.
- **IDs:** type prefix + monotonic counter from one per-run allocator (`P0007`, `S0003`, `CL0102`, `EV0450`). Never UUIDs.

## 1. Tick model
- 1 tick = 1 day. Season = 30 ticks, year = 120 ticks (SPRING, SUMMER, AUTUMN, WINTER). Default run 3 years (360 ticks).
- Round = 10 ticks → 3 cognition rounds/season, 36/year per civ. Configurable `cognition_every_ticks`.
- **Phases per tick (fixed order):**
  0. `interventions` — apply scheduled player interventions
  1. `environment` — weather, river level (upstream→downstream lag), moisture, vegetation/wild-food regrowth, crop growth, spoilage, fire spread
  2. `needs` — consumption, hunger/fatigue, health, deaths
  3. `routine` — per-person policy: eat, rest, flee; idle people take civ tasks by allocation share
  4. `tasks` — movement (deterministic A*, ties by `(y,x)`), task progress
  5. `conflict` — contested resources, combat, trade exchange
  6. `events` — emit Events, derive Evidence for witnesses
  7. `memory` — claims from evidence; carrier decay; loss check (last carrier gone → `KNOWLEDGE_INACCESSIBLE`)
  8. `checkpoint` — tick hash
- **Cognition barrier (research mode):** at round end tick T, freeze one Observation per civ; collect all proposals (timeout = infrastructure failure); validate in a seeded civ permutation; commit accepted tasks at start of T+1. Wall-clock never feeds world time.
- **Long-running tasks:** `Task{task_id, civ_id, origin:(decision_id, action_idx), kind, target, assigned:[person_id], progress, required, status: PENDING|ACTIVE|BLOCKED|DONE|FAILED|CANCELLED, started_tick, deadline_tick, block_reason}`. Progress per tick = Σ worker_labor, `worker_labor = 1000 × health/1000 × (1000+skill/2)/1000 × tool_mod‰`. Proposals may `cancel_task`; anything not mentioned continues.

## 2. Entities
- **Tile** `{x, y, terrain: RIVER|FLOODPLAIN|GRASS|FOREST|HILLS|ROCK|MARSH, elevation, fertility 0–1000, moisture 0–1000, biomass, wild_food, wood, stone, clay, fish (RIVER), crop{seed_type, planted_tick, growth}|null, fire 0–1000, structure_id|null, traces[]}`
- **Materials:** `WILD_FOOD, GRAIN, FISH, SEED_GRAIN, WOOD, STONE, CLAY, FIBER, ASH, PRESERVED_FOOD, FIRED_POT, STONE_EDGE, TABLET` (last three are artifacts with `item_id`, `made_by_rule`).
- **Person** `{person_id, civ_id, settlement_id, age_days, alive, tile, hunger, fatigue, warmth, health, skills{process_key}, carry{material} (cap 20 000 mu), task_id, claim_holdings{claim_id: fidelity}}`. Births/aging deaths *[ext]*.
- **Structure** `{structure_id, type: HUT|GRANARY|FIRE_PIT|ARCHIVE|PALISADE|KILN, tile, civ_id, integrity, build_progress, storage{}, records[]}`. Costs from rules file (e.g. GRANARY = 40 WOOD + 20 STONE + 300 labor).
- **Settlement** `{settlement_id, civ_id, center_tile, member_ids, store_ids}` — one per civ in v1.
- **Civilization** `{civ_id, display_name, model_profile_id, traits{risk_aversion, aggression, curiosity, horizon}‰, known_tiles{(x,y): last_seen_tick+snapshot}, contacts{}, agreements[], allocation{FOOD, BUILD, EXPLORE, STORE, CRAFT, DEFEND, KNOWLEDGE: % sum 100}, ration_mu}`
- **Ledger:** every mutation writes `{tick, material, delta, source|sink: REGROWTH|HARVEST|CONSUME|SPOIL|BURN|BUILD|CRAFT|TRADE|LOOT|INTERVENTION, ref}`; conservation is checked against it.

## 3. Action contract
**DecisionProposal** (Pydantic, unknown fields rejected):
```
{decision_id ≤64 (idempotency key), civ_id, observation_version "civA:r012:<hash8>",
 actions: [Action] (≤12), allocations {shares, ration_mu} | null, cancel_tasks [task_id],
 cited_evidence_ids (must exist in observation),
 belief_updates [{belief_id|null, statement ≤200, explains_event_ids, support_ids, counter_ids, ritual|null}],
 public_explanation ≤600}
```
`public_explanation` is stored as a model-authored claim, never as the model's real reasoning.

| kind | args | validation (legality only) |
|---|---|---|
| inspect | target_id, workers≤2 | target in observation |
| gather | material, tiles[≤9], workers, max_ticks | tiles known, ≤12 from settlement/party, gatherable |
| store | material, qty_mu, structure_id | own storage structure, qty available |
| plant | tiles, seed_type, qty_mu, workers | seed stock, terrain ∉ {RIVER, ROCK}, tile free |
| build | structure_type, tile, workers | materials reservable, tile buildable, type permitted by usable processes |
| explore | target_tile or direction, workers 1–4, max_ticks≤30 | — |
| migrate | target_tile, members ALL or ids | target known, passable |
| trade | counterparty, offer[], request[], meeting_tile, expires_round | contact exists, offer reserved |
| negotiate | counterparty, type NONAGGRESSION/SHARE_TILES/ALLIANCE/TRIBUTE/MESSAGE, terms, text≤280 | contact exists |
| attack | target, workers, stance RAID/DRIVE_OFF/DESTROY | target visible, contact exists |
| record | claim_ids, medium TABLET/KNOT_CORD, archive_id, scribe_id | scribe holds claim, material, own ARCHIVE |
| teach | claim_id, source person/record, learner_ids≤4 | source holds claim, co-located |
| experiment | inputs[], operation HEAT/STRIKE/SOAK/DRY/BURY/GRIND/COMBINE/SEAL/PLANT_TEST, conditions{tile, duration≤20}, prediction{effect, material/property}, prediction_text, workers≤3 | inputs owned & observed, op in enum |

**Validation pipeline:** schema → civ_id matches caller → observation_version current (else STALE) → duplicate decision_id returns stored result (idempotent) → each action in order against cumulative reservations (labor, materials, ≤1 task/person). Invalid actions dropped, valid ones commit (partial acceptance). ≤1 accepted proposal per civ per round.

**Simultaneous conflicts:** civs in per-tick seeded permutation, persons by id. Contested yield split pro-rata to labor, remainder by seeded draw. Combat after movement: `strength = Σ health × tool_mod × stance_mod`, `P(attacker wins) = sA/(sA+sD)`, palisade +300‰ defender, per-participant casualty draws, loot ≤30% of store. Trades execute only with matched offers and both parties at the meeting tile. **Invariant:** permuting proposal arrival order never changes the state hash.

**Rejection reasons:** `SCHEMA_INVALID, UNKNOWN_ACTION, UNKNOWN_ENTITY, UNAUTHORIZED, STALE_OBSERVATION, DUPLICATE_DECISION, INSUFFICIENT_LABOR, INSUFFICIENT_RESOURCES, PREREQ_PROCESS_UNAVAILABLE, OUT_OF_RANGE, ILLEGAL_TERRAIN, NO_CONTACT, CAP_EXCEEDED, UNSUPPORTED_OPERATION, UNCITED_EVIDENCE, BUDGET_EXHAUSTED, TIMEOUT, PARSE_FAILED`. Internal `NOT_PERCEIVED` is reported to the model as `UNKNOWN_ENTITY` so rejections leak nothing.

## 4. Observation projection
- Tile visible if within Chebyshev radius 4 of a living member or radius 2 of an own structure. Known tiles keep a last-seen snapshot + `seen_tick`.
- Events yield Evidence only for people within perception radius (sight 4, fire/smoke 8, sound 3). River level perceived along river-adjacent tiles.
- **Communication network:** a person's evidence/claims enter the civ pool only if within 3 tiles of the settlement centre at the barrier. Explorers report on return. Intact own archives are accessible.
- `Observation{obs_id, civ_id, round, tick, version, hash, sections}` — sections: self, map_known (RLE), visible_foreigners, recent_evidence (≤40), messages (quoted), accessible_claims (top-30 by FTS + recency, with fidelity), beliefs, last_results, season_calendar. Prompt rendered from this object; prompt hash stored.
- `hidden_cause`, other civs' claims/tasks and unseen true tile state are structurally absent from projection types.

## 5. Knowledge model
- **Event** `{event_id, tick, tiles, kind, effects, hidden_cause: NATURAL|INTERVENTION:<id>|ACTION:<task_id>}` — world truth, observer only.
- **Evidence** `{evidence_id, event_id, observer_person_id, kind: SIGHT|SOUND|TRACE|ARTIFACT|MESSAGE|VISION|EXPERIMENT_RESULT, tick, tile, content, fidelity}`
- **Claim** `{claim_id, origin_civ, kind: OBSERVATION|LOCATION|PROCESS|CAUSAL|SOCIAL|DIVINE_MESSAGE|ARTIFACT_HINT, text, content, process_spec|null, evidence_ids, confidence, parent_claim_id, provenance[{op: WITNESSED|TAUGHT|RECORDED|READ|TRADED|REFUGEE|SEIZED, tick, from, to}]}`
- **Carrier** `{carrier_id, kind: PERSON|RECORD|INSTITUTION[ext], ref, holdings{claim_id: fidelity}}`
- **Belief** `{belief_id, civ_id, statement, explains_event_ids, support_ids, counter_ids, adherents, ritual|null, created_round}` — only from proposals or baseline templates; never affects physics.
- **Decision** `{decision_id, civ_id, round, observation_hash, model_profile_id, prompt_hash, raw_output_ref, parsed, validation[], task_ids, latency_ms, usage}`

**Oral teaching** (3 ticks): learner fidelity = parent × 900‰ hands-on or 750‰ oral, capped by teacher. Each process_spec field omitted with probability `(1000−f)/3 ‰`; numeric params distorted ±`(1000−f)/10`%. Distorted copies are new claims with `parent_claim_id`; contradictions coexist.

**Records:** TABLET = 2 CLAY (needs FIRE_PIT); KNOT_CORD = 1 FIBER. Fidelity = scribe's; no drift, but condition decays (1‰/tick, cord 3‰), unreadable < 200. Archive fire destroys records with probability `fire‰`. Reading = teach from record at 850‰.

**Loss:** last accessible carrier dies/burns/is seized → `KNOWLEDGE_INACCESSIBLE` (observer-only) and the process returns `PREREQ_PROCESS_UNAVAILABLE`. Artifacts persist; inspecting a FIRED_POT gives an `ARTIFACT_HINT` claim without process_spec — motivates experiments, enables nothing.

**Cross-civ transmission:** teach at a meeting tile (with trade); refugees switch civ keeping holdings (`REFUGEE`); raiding an archive moves records (`SEIZED`).

## 6. Experiment and discovery system
Rules in `rules/v1/transformations.yaml`, hashed into the run manifest:
```
R-BURN-01      WOOD≥1000, HEAT, tile_fire or fire_pit, moisture<300 → ASH 200, warmth+300 r1; fail_hint "smoke, no flame"
R-GROW-GRAIN   SEED_GRAIN, PLANT_TEST, fertility≥300, moisture 300–800, SPRING/SUMMER, ≥60 ticks → GRAIN = qty×(4+fertility/250); winter frost → 0
R-SPOIL        passive: open 20‰/tick (summer 35), GRANARY 4, sealed FIRED_POT 1, PRESERVED_FOOD 2
R-DRY-FOOD     WILD_FOOD|FISH, DRY, summer/autumn, no rain, ≥5 ticks → PRESERVED_FOOD 1:1
R-POT-01       CLAY≥500 + WOOD≥1000, HEAT, fire_pit/kiln, ≥3 ticks → FIRED_POT, 600‰ (900 with KILN)
R-EDGE-01      STONE≥500, STRIKE → STONE_EDGE (gather WOOD 1500‰, FIBER 1300‰)
R-SOAK-SEED    SEED_GRAIN, SOAK 1 tick → next planting growth +15%
```
**Flow:** validate inputs/op → match most specific rule → no match: `EXPERIMENT_RESULT{NOTHING}`, inputs consumed, nothing unlocked (explicit failure) → partial match: `fail_hint` evidence → success: evidence + PROCESS claim (fidelity 500) on each worker → prediction scored CORRECT/PARTIAL/WRONG as a metric only.

**Usable process** iff (a) ≥2 independent successful evidence events, (b) an accessible carrier holds a matching claim with fidelity ≥600 and required spec fields, (c) inputs and dependency processes usable. Practice: +50 fidelity (cap 950), +30 skill; fidelity <800 → failure chance `(800−f)‰`.

**Starting knowledge:** both civs R-BURN + gathering. Civ A also R-GROW-GRAIN (f 800, 6 carriers). Civ B also R-DRY-FOOD (f 800, 5 carriers).

**Abstract naming:** `material_naming: abstract` applies a seeded bijection (WOOD→"keth") in prompt rendering/parsing only. Manifest states leakage still possible via observed properties. UI labels outcomes: authored rule / discovered combination / model explanation.

## 7. Divine interventions
`Intervention{intervention_id, channel, target{center, radius≤8 | person_ids | civ_id}, params, scheduled_tick, cost, created_wallclock, note}`; per-channel enable flags and costs in run config; `favor_budget` default 100; all logged and hashed.

| channel | cost | effect | evidence |
|---|---|---|---|
| RAIN | 10 | moisture +40‰/tick in radius, ≤10 ticks | rain seen locally; river rise reaches downstream after 2–4 ticks (downstream civ sees river rise without seeing rain); extinguishes fire |
| DROUGHT | 15 | moisture −30‰/tick, wild-food regrowth ×0.3, ≤30 ticks | wilting crops, low-river traces, dry riverbed |
| STRIKE | 20 | lightning: tile fire 800, structure damage, spreads by fire rule | flash/thunder (sound r8), burned structures, charcoal trace |
| VISION | 3 | private evidence for 1–3 persons | ≤3 symbols from authored vocabulary (FLOOD, SERPENT, RED_SKY, EMPTY_GRANARY, TWO_FIRES, OPEN_HAND…); free-text opt-in; enters civ pool only via the communication network ("P0012 reports a vision") |
| SPEECH | 5 | message evidence, ≤280 chars, radius or whole civ | rendered as quoted, escaped data in `messages`; never in the system prompt; action-shaped text is ignored |

Natural weather (showers, dry spells, ~1 lightning/year) uses the same event kinds so causation is genuinely ambiguous. Ablations: `interventions.enabled={…}`, `memory.enabled`.

## 8. Rule-based baseline policy
- **Person routine (every tick):** eat if hunger > 600; rest if fatigue > 800; flee if a stronger hostile is within 3; else take next task slot by allocation.
- **Civ policy** (`rule_baseline` provider, emits normal DecisionProposals through the same validator), in priority order: food_days < 20 → FOOD 60%; spring with seed → plant best known tiles; autumn → STORE 25% + DRY if usable; no GRANARY and materials → build; curiosity draw → one experiment; process with < 3 carriers → teach 2; ARCHIVE exists → record rarest processes; unknown tiles within 15 → explore with 2; on contact: risk_aversion > 600 → NONAGGRESSION + trade surplus, aggression > 500 & food_days < 10 & visible stores → RAID; unexplained STRIKE/DROUGHT → belief "the sky punishes X" (X = most-executed action last round), ritual reduces X by 20% — a testable behavioural channel.
- **Mock provider** replays fixture proposals keyed by `(scenario, civ, round)`; labelled `provider=mock` everywhere.

## 9. Starter scenario: "Shared River"
- River N→S from (20,0) to (44,63), floodplain 2 tiles each side; forest on east hills (x>48), rock west (x<10), clay at 3 bends, fish in river; spring flood +100 floodplain fertility/year.
- **Civ A "Upstream"** at (22,12): risk_aversion 700, aggression 200, curiosity 300, horizon 800.
- **Civ B "Downstream"** at (40,50): risk_aversion 300, aggression 600, curiosity 500, horizon 300.
- ~38 tiles apart, no mutual visibility; contact requires exploration.
- Each civ: 30 people, 30 days food, 400 000 mu seed, 20 WOOD, 10 STONE. Wild food peaks summer, 30% autumn, 0 winter. Start day 1 of spring. Upstream drought / over-fishing hurts downstream. Carrying capacity ~70 people in year 1 without farming expansion.

**Metrics:** survival; food security (food-days per capita, spoilage); knowledge retention (carriers, max fidelity, lost/recovered processes, intact records); adaptation (rounds from event to measurable change in *executed* labor/storage vs seed-matched control); conflict/cooperation; decision validity (rejections by reason, stale, duplicate, parse failures, timeouts); discovery (experiments, rules triggered, prediction accuracy, processes made usable); cost (latency p50/p95, tokens, cost or "unknown").

**Test invariants:** ledger balances, no negatives; ≤1 task/person; mutating civ B private state leaves civ A's observation hash unchanged; `hidden_cause` never serialized into observations/prompts; permuting proposal order → same hash; recorded replay matches every checkpoint hash; branches carry `parent_run_id` + `parent_checkpoint`; killing all R-GROW-GRAIN carriers makes `plant` fail with PREREQ and reading an intact TABLET restores it; speech containing JSON actions changes nothing beyond message evidence; unsupported experiments yield NOTHING; across 20 seeds DROUGHT on A changes executed baseline allocations vs control (statistical, fixed tolerance).

## 10. Epics (milestones A–F)
| # | Epic | Acceptance |
|---|---|---|
| E1 | Repo, decision log, rules/scenario layout (A) | README skeleton; decisions log; `rules/v1` loads with schema validation, hash recorded |
| E2 | Deterministic core (B) | RNG streams, fixed-point helpers, canonical hash; phase-ordered tick loop; same seed → same hash after 360 empty ticks |
| E3 | World gen + environment (B) | Shared River from seed; seasons, moisture, regrowth, river lag, fire, spoilage — unit tested |
| E4 | People, needs, movement, routine (B) | hunger/health/death; deterministic A*; predictable starvation scenario; conservation holds |
| E5 | Action contract, validator, task executor (B) | 13 action schemas; every rejection reason tested; partial acceptance; idempotency; stale rejection |
| E6 | Baseline policy + headless demo (B) | `gf run --scenario shared_river --ticks 360 --headless` completes without credentials, emits metrics |
| E7 | Persistence, replay, branching (B/C) | SQLite manifest/decisions/snapshots/RNG; save/resume and replay hash-identical; branch provenance |
| E8 | Observation projection (C) | visibility, witnesses, comm network; leakage + hidden-cause tests; observation hash per round |
| E9 | Cognition scheduler + providers (C) | barrier, timeouts, budgets, mock + rule providers, one local + one cloud adapter (live qualification may be blocked by credentials — disclosed); mixed-profile fixture run |
| E10 | Knowledge model (D) | claims, carriers, teaching distortion, records, loss, artifact hints, refugee/seizure provenance; carrier-loss/record-recovery test |
| E11 | Experiment system (D) | rule matcher, NOTHING path, ≥2-evidence threshold, practice, abstract naming |
| E12 | Interventions (D) | five channels with flags, costs, logs; geographic evidence; vision/speech as observations only; drought→executed-behaviour test |
| E13 | Contact, trade, negotiation, conflict (E) | first-contact event; matched trades; agreements; combat order test |
| E14 | Research API + inspection client (E) | loopback FastAPI: pause/step/intervene/inspect; event→evidence→belief→decision→task→outcome traversal; branch from UI |
| E15 | Batch runner, metrics, exports, benchmark (F) | `gf batch --seeds 1..20 --profiles …` with model rotation across positions; CSV/JSONL; ablations; benchmark command |

Extension points (not built): births/aging, institutions as carriers, multiple settlements, hydrology/irrigation, rules v2 (metallurgy+), map chunking for larger worlds.
