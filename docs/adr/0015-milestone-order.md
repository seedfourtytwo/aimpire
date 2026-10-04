# ADR-0015: Milestone order

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** creator (order agreed in the planning review, 2026-10-04)
- **Supersedes:** the ladder order in ADR-0010 section 1. The rest of ADR-0010 stands: logic first, dots before graphics, every layer switchable, tested and paired with an AI experiment.
- **Research:** [`80-plan-review-2026-10-04.md`](../research/80-plan-review-2026-10-04.md)

## Context
ADR-0010 ordered the work as a ladder L0 to L8. That order left the god's speech and visions to L7, the eighth of nine levels, and a second model-driven group to L4. Those two things are what set the project apart: no study was found that measures how models treat an unseen authority, and different models sharing one world is the project's signature. The first ladder levels, by contrast, overlap published experiments.

The creator's stated main goal is emergence: to see what kinds of civilization, political system and religion arise when the models make their own decisions, and to trace parallels with real history (ADR-0019).

## Decision

### Order
| Step | Name | Adds | From the old ladder |
|---|---|---|---|
| F1–F6 | Foundation | deterministic core, ledger, dot viewer, mind interface, live adapters, batch runner | Phase 1, plus the missing AI plumbing |
| **M0** | Petri dish | one group, one regrowing food, named places | L0 |
| **M1** | Seasons and a voice | terrain, river, seasons, storage, weather; signs, omens, a voice, prayer; journal and chronicle; run store with branching; minimal web console | L2, with speech and visions pulled forward from L7 |
| **M2** | Two tribes | a second group on another model; contact, messages, gifts, barter, raids, territory | L4, with simple exchange from L5 |
| **M3** | Generations | births, aging, death, inheritance, succession; knowledge carriers, teaching, records, loss; scripture | L1, with carriers from L6 |
| **M4** | Living world | prey, predators, hunting, disease | L3 |
| **M5** | Knowledge | experiments, rule tables generated per seed, discovery | L6 |
| **M6** | Exchange | households, trade, obligations | L5 |
| **M7** | Belief | what the society does with the voice: roles for hearers, shared rites, splits; the god's power economy | L7 |
| **M8** | Rule | rules about rules, offices, factions, fission | L8 |

M6 to M8 are designed around primitives, not named institutions (ADR-0019). Their detailed design is written when M5 closes.

### Dependencies
- F1 → F2 → F3 → (F4 and F5 in parallel) → F6 → M0 → M1.
- M2 and M3 each need M1 and do not need each other. M2 comes first by default.
- M4 needs M3. M5 needs M3. M6 needs M2 and M3. M7 needs M5 and M6. M8 needs M7.
- A research track on native minds (ADR-0018) may start after M2 and is never on the critical path.

### The gate for every milestone
A milestone is done when all four hold:

1. Its physics tests pass on rule baselines, as ensemble tests over seeds.
2. One pre-registered AI experiment has been run and written up (ADR-0014).
3. The result can be watched: a replay exists and plays in the static viewer.
4. `docs/agents/STATUS.md` and the roadmap are updated.

### Named presets
Each milestone is a named configuration preset (`m0`, `m1`, …). CI tests presets only, never arbitrary combinations of layer switches.

## Alternatives considered
- **Keep the ladder order.** Builds population dynamics first, as the creator originally asked, but leaves the god's voice and rival models for many months.
- **Generations before two tribes.** Possible, since they are independent. Rival models need only three-year runs, so they deliver the signature result sooner.

## Consequences
- Births arrive at the fourth milestone instead of the second.
- The first playable build is M1: the player sends a sign or speaks, and the tribe answers.
- The roadmap in `docs/plan/roadmap.md` is the working copy of this order.
- Revisit the M2/M3 order if population dynamics become the creator's priority.

## References
- ADR-0010, ADR-0017, ADR-0018, ADR-0019.
