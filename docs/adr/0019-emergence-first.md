# ADR-0019: Emergence first: primitives, not institutions

- **Status:** Accepted (creator, 2026-10-04)
- **Date:** 2026-10-04
- **Deciders:** creator (goal stated by the creator, 2026-10-04; rules proposed by the planning review)
- **Replaces:** the unfiled "ADR-0012: Social systems" draft in research note 70 as the governing principle for M6 to M8. That note remains the reference for individual-level rule models and validation patterns.

## Context
The creator's main goal, in his words: let the models make their own decisions and see what kind of civilization, political system and religion emerges, play with those emergent behaviours, and trace parallels with the real world.

The draft social design works against that goal in one way. It enumerates institutions in code: polity types (`BAND | CHIEFDOM | COUNCIL | ASSEMBLY`), succession types, property regimes, a doctrine with six fixed features. A society can then only pick from a menu the developers wrote. Whatever it picks, nothing emerged.

Two further limits:

- **One mind per civilization cannot have politics.** It can only announce them. Politics needs several decision makers with different interests.
- **A pretrained model may be reciting history** (ADR-0018). A parallel is only interesting if the mind could not simply have remembered it.

## Decision

### 1. Author physics and primitives. Never author institutions.
The engine provides bodies, needs, space, time, materials and a small set of social primitives that name no institution:

| Primitive | What it is |
|---|---|
| **Control** | who may take from, enter or use a store, tile or object |
| **Obligation** | X owes Y an amount of something by a time |
| **Rule** | a statement the engine can check: who, may / must / must not, do what, when, or else what |
| **Role** | a named bundle of permissions that a society creates; the name is free text |
| **Procedure** | a rule about how rules change: whose consent is needed |
| **Sanction** | take goods, exclude, strike |
| **Assembly** | people gather at a place for a stated purpose and may consume goods |

Rules follow the shape of Crawford and Ostrom's institutional grammar (who, deontic, action, conditions, or-else). They are typed so the simulation can check compliance, and enforcement happens only if the society assigns someone to enforce.

Forbidden in engine code, rules data and prompts: any enumeration of regime types, succession types or property regimes; any fixed list of doctrine features; any role with a built-in name such as chief, priest or king; any technology tree.

### 2. Individual psychology is allowed, and is labelled as an assumption
People who are not minds follow rules: eat, rest, flee, copy a neighbour, comply or shirk. Those rules are a model of human behaviour and they shape what can emerge. Each one must be minimal, drawn from a cited source, documented as an assumption, and switchable so its effect can be measured.

### 3. Names live in the observer layer
- Words such as chiefdom, tribute, priesthood, schism or market appear only in the **observer layer**: detectors that run on a finished run's data and label what happened.
- Each label has an operational definition over simulation data. For example, tribute: at least a set share of harvest flows through one store controlled by a small share of households for a set number of seasons.
- A model acting as historian may propose parallels with real history. It runs outside the simulation and its output is marked as interpretation. Nothing from the observer layer flows back into a run.

### 4. Neutral prompts
- A mind's system prompt says what it stands for, what it can perceive and the reply format. It suggests no institution, belief or strategy.
- A lexicon check fails CI if a prompt template contains a word from the banned list (king, chief, priest, tax, law, religion, god, democracy, market and so on). The list is versioned.
- Observations describe events in plain physical terms (ADR-0017 section 5).

### 5. More than one mind, when politics is the question
- `minds.granularity` is a run setting: `civ` (one mind per group), `household` (one per household head, at a slower cadence), later `sampled` (a sample of individuals).
- M0 to M5 gate on `civ`. From M3, when households exist, `household` is available as an experiment.
- M6 to M8 are designed for `household`. A group's decisions then come out of whatever procedure its members have set up, and the engine only applies it.

### 6. The emergence ledger
A claim that something emerged is entered in `docs/experiments/ledger.md` with four items:

1. **Not scripted.** No code path, rule file or prompt names it or produces it directly. The audit is a search, and it is recorded.
2. **How often.** The share of seeds in which it appeared, with the conditions.
3. **Against what.** Its rate under rule baselines and under at least one ablation (no voice, no messages, no storage, as fits).
4. **Which knowledge arm** (ADR-0018). Seen only in A0: "possibly recalled". Seen in A2 or A3: "emergent".

### 7. Parallels with real history
- The observer layer holds a small library of patterns from the literature, each with its definition and source: inequality rising with storage, groups splitting as they grow, shared rites delaying splits, and others from research note 70.
- A parallel is reported as a rate across seeds beside the historical claim it resembles, never as a single anecdote.
- Whether to seed scenarios from real geographies stays an open question.

## Alternatives considered
- **Enumerated institutions with rule-based dynamics** (the note 70 draft). Testable against known models, but the outcome space is the developers' menu.
- **Free-text institutions with a model as referee.** Unlimited, but breaks the rule that code, not a model, decides what happens.
- **One mind per person.** The purest version, and too costly today. `sampled` keeps the door open.

## Consequences
- M6 to M8 need a small rule language and a checker. That is more design work than a menu of regimes, and it is where the project's main result will come from.
- Some published social models in note 70 survive as individual-level assumptions and as observer-layer tests. Others, such as enumerated polity types, are dropped.
- Household minds multiply model calls. They run at a slower cadence and on small models.
- Results become claims of the form "in arm A2, across 40 seeds, a rule concentrating control of the store in one household appeared in 30% of worlds", which is the kind of claim a reviewer can check.
- Revisit the primitive list when M6 is designed. It should stay short.

## References
- Crawford and Ostrom, "A Grammar of Institutions" (1995).
- ADR-0017, ADR-0018; research note 70 (models and validation patterns); the review's sections on game and research design.
