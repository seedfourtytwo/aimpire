# Roadmap

Strategy (ADR-0010): **logic first, simple physics, AI in the loop from day one, then add one layer of complexity at a time.** Graphics are dots until the logic earns better.

## Phase 0 — Planning ✅
Spec, research, ADRs 0001–0010, CI skeleton, agent conventions.

## Phase 1 — Engine foundation (needed before L0)
| Epic | Deliverable | Tests (written first) |
|---|---|---|
| **F1** Repo bootstrap | `sim/` uv project; justfile recipes `lint`, `typecheck`, `test`, `check-sim`; CI python job goes live | CI green on an empty package |
| **F2** Deterministic core | counter RNG, fixed-point helpers, canonical hash, plug-in system scheduler (ordered systems, per-system rate, on/off via config) | same seed → same hash; permuted registration order → error, not drift |
| **F3** Ledger & invariants | conserved-quantity ledger, debug-mode invariant checks per system | no negatives; sources − sinks balance every tick |
| **F4** Run output & viewer | metrics time-series, PNG/GIF frame renderer (dots), Markdown "lab notebook" per run, replay export + static Canvas2D player | golden image hash for a seeded 10-tick run |

## Phase 2 — The ladder (ADR-0010)
Each level is done only when: its physics tests pass, the rule baseline runs, and an AI experiment report is written (`docs/experiments/`).

| Level | Physics & rules | AI hook | Validation |
|---|---|---|---|
| **L0 Petri dish** | grid, regrowing food, agents with energy: move, eat, starve | action contract (move/forage/stay) + mock + one real-model profile | food regrowth curve; energy conservation; random vs greedy vs LLM foraging |
| **L1 Life cycle** | birth, aging, death; inheritance | ration / disperse allocations | emergent carrying capacity; logistic-like growth |
| **L2 Terrain & weather** | elevation, river, moisture, seasons, rain/drought interventions | observation of weather; store/move decisions | seasonal cycles; drought → measurable behaviour change |
| **L3 Ecology & disease** | prey, predators, hunting; SEIR contagion | avoid/quarantine/hunt decisions | Lotka–Volterra oscillation; SIR curve shape |
| **L4 Groups & conflict** | 2+ groups, territory, contact, combat | raid / defend / negotiate | Lanchester sanity; permutation-invariant resolution |
| **L5 Trade** | goods, barter, specialisation | trade offers | price convergence; inequality (Gini) emerges |
| **L6 Knowledge** | experiments, teaching, records, loss | experiment / teach / record | carrier-loss blocks process; records restore it |
| **L7 Belief & religion** | visions, speech, beliefs, rituals, sects | belief updates cite evidence | speech can't bypass validation; sect fission under drift |
| **L8 Politics** | leaders, factions, institutions, fission | minds per polity (+ role minds later) | group fission at size thresholds; legitimacy dynamics |

Persistence (save, replay, branch) arrives with F4 as replay export, and fully alongside L1 (ADR-0004).
The research API and live interventions UI arrive alongside L2.
The PixiJS/React client (ADR-0002) is deferred.

## First sprint (parallel agent sessions)
1. **Agent A:** F1 → F2 (core + scheduler).
2. **Agent B:** F4 viewer + metrics, against a stub world. It can start once F1 lands.
3. **Agent C:** after F2, the L0 physics: food field, energy agents, rule baselines.

Then L0's AI experiment: an LLM group-mind vs rules, on matched seeds.
