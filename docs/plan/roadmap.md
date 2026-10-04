# Roadmap

**Goal.** Let model-driven societies make their own decisions and see what emerges: what kind of civilization, what political order, what beliefs. Then trace parallels with real history. The player is a god who can nudge and speak but never command.

**Strategy.** Logic first, dots before graphics (ADR-0010). Build a thin slice of the whole loop early, then deepen it (ADR-0015). Author physics and primitives, never institutions (ADR-0019).

The order below was accepted by the creator on 2026-10-04. It replaces the L0 to L8 ladder order. Detailed issue specs for the first steps are in [`backlog.md`](backlog.md).

## Phase 0 — Planning ✅
Spec, research, ADRs 0001–0010, CI skeleton, agent conventions. Then the planning review and ADRs 0011–0019.

## Phase 1 — Foundation
No live model is needed until F6. Tests are written first (ADR-0016).

| Epic | Deliverable | Gate |
|---|---|---|
| **G1** Guard rails | Protected paths hook, CI path check, acceptance-test folder, review workflow, task template | A test pull request that touches a protected path is blocked |
| **F1** Bootstrap | `sim/` uv project, package skeleton, `just` recipes, import rules, banned-API lint | `just check` green on the empty package |
| **F2** Deterministic core | calendar, fixed-point helpers, draw function, turn order, ids, state hash, scheduler with presets (ADR-0011, ADR-0012) | Same seed gives the same hash; integer results match exact fractions; known-answer draw vectors match |
| **F3** Ledger and invariants | conserved-quantity ledger, invariant checks per system | No negatives; sources minus sinks balance every tick |
| **F4** Watch | metrics series, dot frames, replay file, static replay player, lab notebook per run | A replay file renders identically twice |
| **F5** Mind interface v0 | provider protocol; mock, rule and recorded providers; places; observation builder; reply schema; validator; decision log; budgets (ADR-0013) | An invalid reply never changes state; recorded replay matches every hash |
| **F6** Live and batch | OpenAI-compatible and Anthropic adapters; qualification; batch runner with paired seeds, replicates and seats; report generator (ADR-0014) | Budget caps refuse a call that would exceed them; two or three models qualified |

Dependencies: G1 → F1 → F2 → F3 → (F4 and F5 in parallel) → F6.

## Phase 2 — Milestones
Each milestone is a named preset (`m0`, `m1`, …). It is done when its physics tests pass on rule baselines, one pre-registered AI experiment is written up, a replay can be watched, and status files are updated.

| Milestone | Adds | Gate on rule baselines | AI experiment |
|---|---|---|---|
| **M0 Petri dish** | one group, one regrowing food, named places | an empty map settles at the predicted stock; a harvest sweep peaks near half-full stock | harvest policy against random, greedy and optimal rules; regrowth rule disclosed or hidden; places or grid |
| **M1 Seasons and a voice** | terrain, river, seasons, storage, spoilage, weather; signs, omens, a voice heard by one person, prayer (ADR-0017); journal and chronicle; run store with branching; minimal web console | drought changes executed work against a control; a voice message cannot bypass validation | unexplained drought; true, false and harmful messages from the voice; coincidence against intervention; what they pray for |
| **M2 Two tribes** | a second group on another model; contact, messages, gifts, barter, raids, territory | shuffling proposal order leaves the hash unchanged; ordinary fights kill under 10% | mixed-model pairings with seats rotated; a scarcity sweep; promises kept or broken |
| **M3 Generations** | births, aging, death, inheritance, succession; households; knowledge carriers, teaching, records, loss; dictation and inscription | the population plateau scales with food; growth slows as numbers rise; losing every carrier of a skill blocks it and a surviving record restores it | population policy; what survives a leader's death; how a message drifts over generations; first runs with household minds |
| **M4 Living world** | prey with their own food; predators; hunting; disease that can return | both species persist in k of n seeds; predators lag prey; the share infected in an outbreak falls in an expected range | avoidance, quarantine, overhunting |
| **M5 Knowledge** | experiments on materials; rule tables generated per seed (ADR-0018) | an unsupported experiment yields nothing; a process becomes usable only after two independent successes | discovery in familiar and unfamiliar worlds; the familiarity gap |
| **M6 Exchange** | households as owners; trade, gifts, obligations; the control and obligation primitives (ADR-0019) | prices converge in a trading fixture; inequality responds to storage | what exchange arrangements appear, by knowledge arm |
| **M7 Belief** | what a society does with the voice: roles for hearers, shared assemblies, splits; the god's power economy | belief never changes physics; a message cannot be made true by repetition | how groups explain the voice; when they split |
| **M8 Rule** | rules about rules, roles, sanctions, fission; household minds by default | rule checking is exact; fission hazard rises with group size | what orders of rule appear, how they change, how they end |

M2 and M3 do not depend on each other. M2 comes first by default; swap them if population dynamics matter more than rivalry.

M6 to M8 are designed in detail when M5 closes, around primitives and not named institutions.

## Lab track — the Tinkering Lab (ADR-0020, proposed)
A workshop for "what if" questions: change one thing (gravity, rain, a mind's settings, a tribe's size) and compare against the same world on the same seeds. World rates are derived from a few fundamental constants, so a small change in gravity moves walking speed, carry load, river speed and tree height together. Design: [`research/90`](../research/90-tinkering-lab-and-world-physics.md).

| Step | Lands with | Deliverable |
|---|---|---|
| **W0** World constants | M0a | `rules/v1/world.yaml`; integer scaling laws; identity at Earth |
| **LAB0** Knobs | M0a | knob registry, schema export, `--set`, `beyond-model` tag |
| **LAB1** Twin worlds | M0b | `aimpire lab twin` with a first-divergence report |
| **LAB2** Sweeps | M0d | `aimpire lab sweep`, phase-diagram small multiples |
| **LAB3** Forks and world events | M1 | branch from a checkpoint; scheduled knob changes |
| **LAB4** Workshop page | M1 web console | sliders, derived-value preview, run queue, gallery |

Lab runs are exploratory. A finding counts only after a pre-registered re-run (ADR-0014).

## Side tracks
| Track | Starts | What |
|---|---|---|
| **Native minds** (ADR-0018) | after M2 | train a small model on in-world text only; put it through M0 qualification; decide on that result |
| **Observer layer** (ADR-0019) | with M2 | detectors that label patterns in finished runs; the emergence ledger; parallels with real history |
| **Web client** (ADR-0002) | console at M1; full client when the logic earns it | pause, step, intervene, read the chronicle, follow the sent-to-done chain, fork a timeline |

## From the old ladder
| Old level | Now |
|---|---|
| L0 Petri dish | M0 |
| L1 Life cycle | M3 |
| L2 Terrain and weather | M1 |
| L3 Ecology and disease | M4 |
| L4 Groups and conflict | M2 |
| L5 Trade | M6, with simple barter in M2 |
| L6 Knowledge | M3 (carriers, teaching, records) and M5 (experiments) |
| L7 Belief | the voice in M1; the rest in M7 |
| L8 Politics | M8 |

## First sprint
1. **Creator:** merge the planning change; answer the open questions; push the CI path check from G1.
2. **Strong model:** G1, then acceptance tests for F1 and F2.
3. **Implementing agents:** F1, then F2 in the order given in the backlog.
4. Once F3 lands: F4 and F5 in parallel sessions.
