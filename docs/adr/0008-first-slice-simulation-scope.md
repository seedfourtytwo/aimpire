# ADR-0008: First-slice simulation scope (rules v1)

- **Status:** Proposed
- **Date:** 2026-10-04
- **Research:** [`docs/research/50-simulation-design.md`](../research/50-simulation-design.md) is the full design.

## Context
The spec asks for a small, observable world before any campaign ambition. Two choices were left to defaults:
- bounded material experiments, or deep physical invention
- civilization controllers, or faction minds

The creator wants a mix of fun god-game and historical parallels, where AI civilizations develop their own history.

## Decision
- **Scenario "Shared River":** 64×64 tiles, two civilizations of 30 people each.
  - *Upstream* is cautious and long-horizon.
  - *Downstream* is aggressive and short-horizon.
  - Seasonal food is limited, and the two start out of contact.
- **Time:**
  - 1 tick = 1 day; 30-tick seasons; 120-tick years.
  - A cognition round every 10 ticks, giving 36 rounds per civilization per year.
  - Default run length is 3 years.
- **One cognition controller per civilization**, declared as an approximation of collective decision-making. Faction minds are an extension point, not v1.
- **Bounded experiment system** over authored rules in `rules/v1/transformations.yaml`: burn, grow, spoil, dry, pottery, stone edge, seed soaking.
  - A process becomes usable only with at least 2 independent successful evidence events, a carrier with fidelity ≥600, and its dependencies.
  - Unsupported experiments yield `NOTHING`.
  - An abstract material-naming mode is available; residual knowledge leakage is disclosed.
- **13 allowlisted actions:**
  - inspect, gather, store, plant, build, explore, migrate
  - trade, negotiate, attack
  - record, teach, experiment

  Each has a typed schema and a closed enum of rejection reasons. Partial acceptance is allowed and duplicates are idempotent.
- **Knowledge** is held by carriers: people and records.
  - Oral teaching omits and distorts according to fidelity.
  - Records need materials and decay.
  - Death or fire removes access to knowledge, and artifacts can only hint at a lost process.
  - Trade, refugees and raids transmit knowledge with provenance.
- **Five intervention channels:** RAIN, DROUGHT, STRIKE, VISION (symbolic vocabulary by default) and SPEECH.
  - Each can be enabled or disabled, has a cost and is logged.
  - Natural weather uses the same event kinds, so cause stays ambiguous.
  - Speech and visions only ever appear as quoted observation data.
- **Historical-parallel layer (creator request):** the observer UI can tag emergent patterns against a small library of historical analogues, such as "granary state", "upstream/downstream water conflict", "oral tradition loss" or "cargo-cult ritual". Tags are *labels on executed behaviour, written by the observer*, never inputs to the simulation. This is an E14/E15 feature, not core.
- **Out of scope for v1:** births and aging, multiple settlements per civilization, hydrology and irrigation, institutions as carriers, metallurgy and later eras.

## Consequences
- The 15 epics in the roadmap are concrete and testable.
- The game feel comes from emergent consequences and the observer's narrative tools, not from scripted events.
