# Glossary

The project's shared vocabulary. Code, tests, docs and UI use these words with these meanings
(AGENTS.md §4.2). Add a term here in the same PR that introduces it. Sources: ADR-0004, ADR-0007,
ADR-0008 and [research 50](research/50-simulation-design.md).

## Time

| Term | Meaning |
|---|---|
| **tick** | One simulated day; the unit of world time. Never derived from wall-clock time. |
| **season / year** | 30 ticks / 120 ticks (rules v1). |
| **cognition round** | Every 10 ticks each civilization receives one observation and may return one decision. |
| **barrier** | The point where the scheduler waits for every civilization's decision (or timeout) before any is applied, so faster models gain no turns. |
| **phase order** | The fixed order of work inside a tick: interventions → environment → needs → routine → tasks → conflict → events → memory → checkpoint. |

## World and people

| Term | Meaning |
|---|---|
| **civilization (civ)** | A society with one cognition controller (an approximation of collective decision-making). |
| **person** | A simulated individual with needs, health, location, labour and memories; moved by cheap routine policies. |
| **settlement** | A civ's home cluster of structures and storage. |
| **tile / field** | A map cell / a whole-map integer layer (moisture, vegetation, soil…). |
| **milli-unit (mu)** | Integer quantity unit; 1 food unit = 1 person-day = 1000 mu. |
| **permille (‰)** | Integer probability or rate out of 1000. |
| **ledger** | The record of every resource change; with declared **sources** and **sinks** it must balance. |

## Knowledge

| Term | Meaning |
|---|---|
| **event** | Something that happened (truth), with location, tick, witnesses and an optional `hidden_cause`. |
| **evidence** | What a specific witness perceived of an event. Never contains `hidden_cause`. |
| **claim** | A statement a civ holds, with confidence, supporting evidence and dependencies. |
| **belief** | A proposed explanation (e.g. about the god), with supporters, counter-evidence and rituals. |
| **carrier** | Who or what holds a claim: a person or a record. Knowledge exists only while a carrier can access it. |
| **record** | A physical carrier (e.g. carved marks) that needs material, storage and access, and decays. |
| **fidelity** | Integer quality (0–1000) of a carrier's copy of a claim; teaching can lower it. |
| **process** | An authored transformation (burn, grow, dry…) a civ can use once enough evidence, a carrier with fidelity ≥ 600 and its dependencies exist. |
| **experiment** | An action testing materials with an operation and a prediction; unsupported combinations yield `NOTHING`. |
| **artifact hint** | A surviving object suggesting a lost process existed, without restoring its procedure. |

## Cognition

| Term | Meaning |
|---|---|
| **observation** | The frozen, access-filtered view one civ receives at a round; identified by version and hash. |
| **proposal** | A model's typed reply: actions, allocations, cited evidence, belief updates, a public explanation. |
| **action** | One of the 13 allowlisted kinds (inspect, gather, store, plant, build, explore, migrate, trade, negotiate, attack, record, teach, experiment). |
| **validation** | Schema check, then sim legality check (ids, access, prerequisites, labour, geography, observation version). |
| **rejection** | A recorded, typed reason an action was refused. Data, not an exception. |
| **task** | An accepted action scheduled for execution in world time. |
| **decision** | The stored record of one round for one civ: observation hash, profile, raw blob, parsed proposal, validation, tasks. |
| **provider** | An adapter that talks to a model: mock, rule, recorded, Anthropic, OpenAI-compatible. |
| **profile** | A named TOML file choosing provider, model, limits, budget and price for a civ. |
| **qualification** | `aimpire qualify`: checks a profile's structured output, action validity, latency and cost. |
| **baseline** | The rule-based policy used as the control in experiments. |

## God and interventions

| Term | Meaning |
|---|---|
| **intervention** | A player act through a **channel**: RAIN, DROUGHT, STRIKE (physical), VISION, SPEECH (communicative). Each is enabled, costed and logged. |
| **vision** | A symbolic message delivered privately to a person or group as observation data. |
| **speech** | Direct words delivered as quoted observation data, never as instructions to the model. |

## Runs and research

| Term | Meaning |
|---|---|
| **run** | One simulation with its manifest, inputs log, events and checkpoints (`runs/<id>/run.db`). |
| **manifest** | Seed, rules version, schema version, runtime versions, profiles, budgets, git SHA. |
| **inputs log** | Interventions plus stored decisions: the source of truth for replay. |
| **checkpoint / state hash** | A full canonical state snapshot / its BLAKE2b-256 hash, with per-subsystem sub-hashes. |
| **recorded replay** | Re-running a run from its inputs log; must reproduce every checkpoint hash. |
| **fresh rerun** | Same seed, new model calls; explicitly not hash-comparable. |
| **branch** | A new run started from a checkpoint, carrying parent provenance. History is never edited. |
| **golden fixture** | A committed recorded run plus expected hashes, checked in CI. |
| **rules version** | Version of authored world rules; bumping it invalidates hash comparability by design. |
| **provenance label** | `LIVE`, `RECORDED`, `FIXTURE` or `BASELINE` on every decision and output. |
| **historical-parallel tag** | An observer-written label linking executed behaviour to a historical analogue; never an input to the sim. |
