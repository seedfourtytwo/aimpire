# Roadmap

The spec's milestones A–F are broken into 15 epics (E1–E15). Full acceptance criteria are in [`../research/50-simulation-design.md`](../research/50-simulation-design.md) §10. Each epic becomes a GitHub issue labelled `epic`. Its child issues each fit one agent session and one PR.

## Phase 0 — Planning (this PR) ✅
Spec captured, five research tracks, ADRs 0001–0009, CI skeleton, agent conventions.

## Milestone B — Deterministic core, headless demo
| Epic | Deliverable | Parallelisable with |
|---|---|---|
| **E1** Repo bootstrap | `sim/` uv project, justfile recipes live, `rules/v1` loader + schema, decisions log | — (first) |
| **E2** Deterministic core | counter RNG, fixed-point, canonical hash, phase-ordered tick loop; 360 empty ticks hash-stable | — (after E1) |
| **E3** World gen + environment | Shared River map from seed; seasons, moisture, regrowth, river lag, fire, spoilage | E4 |
| **E4** People, needs, movement | hunger/health/death, deterministic A*, routine policy, ledger conservation | E3 |
| **E5** Action contract | 13 action schemas, validator with all rejection reasons, task executor, idempotency | after E2 |
| **E6** Baseline + headless demo | `aimpire run --scenario shared_river --ticks 360 --headless` with metrics, no credentials | after E3–E5 |
| **E7** Persistence, replay, branching | SQLite run db, checkpoints, recorded replay hash-identical, branch provenance; golden fixtures in CI | after E6 |

## Milestone C — Cognition
| **E8** Observation projection | visibility, witnesses, communication network; leakage + hidden-cause tests | E9 |
| **E9** Scheduler + providers | barrier, budgets, mock/rule/recorded, Anthropic + OpenAI-compat adapters, profiles, `qualify` | E8 |

## Milestone D — Knowledge & gods
| **E10** Knowledge model | claims, carriers, teaching distortion, records, loss, artifact hints, cross-civ transmission | E11 |
| **E11** Experiment system | rule matcher, NOTHING path, usability threshold, practice, abstract naming | E10 |
| **E12** Interventions | RAIN/DROUGHT/STRIKE/VISION/SPEECH with evidence geography; drought → executed-behaviour test | after E10 |

## Milestone E — Contact & interface
| **E13** Contact, trade, conflict | first contact, matched trades, agreements, combat ordering | E14 |
| **E14** Research API + web client | FastAPI on loopback; web client: map, inspector, link tracer, timeline, interventions, branch | E13 |

The client prototype (ADR-0002 §"first de-risking prototype") **can start right after E1**, using a fake replay bundle. It does not depend on the sim.

## Milestone F — Experiments
| **E15** Batch + exports + benchmark | `aimpire batch` over seeds × profiles with position rotation, ablations, CSV/JSONL, Pages replay demos, historical-parallel tags |

## Suggested first sprint (parallel agent sessions)
1. **Agent A:** E1 then E2 (sim core).
2. **Agent B:** client prototype with procedural art, fake replay, Pages deploy (ADR-0002 exit criteria).
3. **Agent C:** after E1 lands, E3 (world gen + environment).

Each agent works in its own branch and worktree, and ends by updating [`../agents/STATUS.md`](../agents/STATUS.md).
