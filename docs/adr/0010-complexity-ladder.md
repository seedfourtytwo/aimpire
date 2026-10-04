# ADR-0010: Logic first, complexity ladder, dot viewer

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** creator
- **Amends:** ADR-0002 (client comes later; dots first), ADR-0008 (the fixed first slice is replaced by the ladder below)

## Context
The creator wants to build the **world physics and rules first, keep them simple, test how AI behaves inside them, then add parameters and complexity step by step.** Graphics come later. People can be single-colour dots on a simple map.

The long-term goal is a real-world-like simulator with:
- population dynamics (reproduction, swarms, predators, disease)
- trade
- religion
- politics
- fighting

## Decision

### 1. The complexity ladder
Each level adds one layer. Every layer is:
- **switchable in config**, so earlier experiments stay reproducible;
- **covered by validation tests**, test-driven;
- **paired with an AI-behaviour experiment**: an LLM mind compared with the rule baseline.

A level is done only when its tests pass and its experiment report exists.

| Level | Adds | Physics / rules | AI experiment |
|---|---|---|---|
| **L0 Petri dish** | flat grid, one food resource that regrows; agents with energy that move, eat and die | integer energy, conserved via a ledger; logistic regrowth; 1 tick = 1 day | Does an LLM group-mind forage better than random walk or a greedy rule? |
| **L1 Life cycle** | birth, aging, death by age, inheritance of energy | demography; carrying capacity *emerges* from food | Does it manage population vs food (e.g. ration, spread out)? |
| **L2 Terrain & weather** | elevation, water/river, seasons, rain/drought; first god interventions (rain, drought) | moisture-driven growth; seasonal cycles | How does it react to unexplained weather? Does it store food? |
| **L3 Ecology & disease** | prey animals, predators, hunting; contagion (SEIR) | predator–prey and epidemic dynamics, validated against Lotka–Volterra and SIR curves | Does it avoid danger, quarantine, overhunt? |
| **L4 Groups & conflict** | two or more groups, territory, contact, fighting | Lanchester-style combat with morale and rout | Cooperate or raid? Does scarcity change it? |
| **L5 Trade** | goods, bilateral barter, specialisation | price discovery, Sugarscape-style | Do trade networks form? Does inequality emerge? |
| **L6 Knowledge** | experiments, teaching, records, loss | authored transformation rules (ADR-0008 experiment system) | Does it discover, preserve, lose processes? |
| **L7 Belief & religion** | visions and speech from the god; beliefs, rituals, sects | cultural transmission (conformity/prestige bias) | Does it explain the god? Does it split into sects? |
| **L8 Politics** | leaders, factions, institutions, fission into new polities | legitimacy, structural-demographic signals | Do states form, collapse, split? |

Later levels follow the long campaign: metallurgy, energy, industrial hazards, and eventually space and the **Great Filter** challenges.

Detailed social-system models (L4–L8) are in [`70-social-systems.md`](../research/70-social-systems.md).

### 2. AI from L0
Cognition plugs in from the first level through the same typed-proposal contract (ADR-0005). It starts with **one mind per group**.

Every experiment runs three conditions on matched seeds:
- the rule baseline
- a mock provider
- at least one real model

The real model may be a local one, or a cheap API model with a small cap.

### 3. Viewer: dots, not graphics
- **Agent-visible:** headless PNG frames, GIF/MP4 clips and time-series charts rendered in Python, so cloud sessions can *see* a run.
- **Creator-visible:** a tiny static page using plain Canvas2D. It plays an exported replay file and works on iPhone via GitHub Pages.
- **Charts follow Tufte principles:** high data-ink ratio, small multiples, no chart junk, direct labels instead of legends where possible.
- The PixiJS/React client in ADR-0002 is deferred until the logic is worth dressing up.

### 4. Engineering standards (creator)
- Test-driven: tests are written first or with the code.
- Clean, commented, modular, reusable code.
- Small files: a soft cap of about 300 lines per module.
- CI/CD on every change.

## Consequences
- The first runnable thing is small: a petri dish with dots and charts.
- Every new parameter has a measured effect, so complexity is earned rather than assumed.
- The rich first slice in ADR-0008 is reached around L2–L6 rather than built at once.
- Ladder levels are config flags, so the engine needs a clean system/plug-in scheduler from day one.
