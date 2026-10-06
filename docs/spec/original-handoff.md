!!! info "Historical intent"
    The creator's original handoff of 2026-10-04, under the working title *Great Filter*. It remains the source of the core intent, but it is not binding: the [vision](../vision.md) holds current intent, and the [ADRs](../adr/README.md) and [roadmap](../plan/roadmap.md) win wherever they differ (name, client stack, build order).

# Original specification (creator handoff, 2026-10-04)

> Verbatim copy of the creator's handoff document. This is the source of intent for the project.
> Where later decisions differ (see `docs/adr/` and `docs/plan/decision-log.md`), the ADRs win.
> Note: the working title in this spec is **Great Filter**; the repository is named **aimpire**.

---

# Great Filter — Claude Code project handoff

## Quick summary

Build a retro civilization research simulator with god-game interactions. Autonomous AI civilizations inhabit the same physical world, make their own decisions, develop beliefs, share or lose knowledge, trade and fight. The player influences them through events, visions and divine speech rather than directly commanding units. Each civilization can use a separately selected cloud or local model. The long-term ambition is a civilization campaign from primitive societies through existential risks toward space, with uncertain outcomes. The first build should establish observable behavior in a small world, not attempt the entire campaign.

Confirmed creator choices: research simulator first; selectable models including local models; different models for different civilizations in the same run; physical interventions, visions and direct speech all available, with their mechanics still open to refinement.

Recommended architecture, not a confirmed creator decision: Python simulation and experiment backend, typed action validation, SQLite records, provider adapters, and a Godot retro visual client. Open questions include hardware, inference budget, society granularity, depth of physical invention, target platform and eventual release model.

---

## 1. Product idea and intended experience

The inspiration is Populous, Black & White and early Age of Empires: an overhead or isometric world with readable retro pixel graphics. Use original placeholder graphics; do not copy copyrighted game assets.

Civilizations are autonomous intelligences. The player is a god who can influence conditions, send dreams or symbols, and speak to selected inhabitants. Civilizations may misunderstand, resist, reinterpret or ignore the player. The player cannot directly order construction, select a research upgrade or command villagers to march somewhere.

The interesting loop is:

Observe → intervene → societies interpret the evidence → societies choose actions → the world produces consequences → inspect changes in behavior, culture and knowledge → intervene again.

Religion is a possible communication mechanism, not mandatory lore. Societies may construct incompatible theories of the player, perform rituals, test correlations, develop skepticism or split into factions. Weather should not automatically imply divine approval.

Long-term campaign ambition: help at least one society survive interacting existential hazards and establish a durable civilization beyond its original planet. Getting to space does not automatically mean every existential risk has been overcome. The Great Filter and Fermi paradox are thematic frames and scenario ideas, not claims that we know their explanation.

Possible later risks include escalating warfare, ecological damage and dangerous technologies. Risks should arise from implemented causal systems and civilization choices. Do not simply draw a hidden catastrophe card and declare that to be emergence.

## 2. Confirmed priorities versus proposals

Confirmed requirements:
- This starts as a research simulator, emphasizing inspection and experiments.
- Users choose among many model providers and local models.
- Different civilizations can use different models in the same world.
- Support physical events, ambiguous visions and direct divine speech. Balance remains adjustable.
- Civilizations maintain evolving knowledge and memory. Knowledge can spread, be distorted, become inaccessible or disappear.
- Multiple societies coexist, discover each other, trade and potentially fight.
- The eventual visual direction is retro and readable.

Proposals you may refine with an explanation:
- Python authoritative simulation backend.
- FastAPI/Pydantic contracts, SQLite persistence and an asynchronous cognition scheduler.
- A provider-independent adapter interface, using LiteLLM where useful.
- Ollama as an initial local route and llama.cpp-compatible endpoints as an alternative.
- Godot/GDScript for the visual client.
- Initially two civilizations with inexpensive simulated villagers and one cognition controller per civilization.

Unresolved: desktop versus browser, actual hardware, spending limits, number of reasoning agents, historical realism versus narrative exploration, physical invention depth and eventual open-source or commercial release.

At the start, ask a compact set of high-impact questions about those issues. Explain recommended defaults. Keep progressing on independent foundational work while answers are pending. If I do not answer, use the conservative prototype defaults below and record them as assumptions. Do not infer authorization to spend money, provision paid resources, publish anything or expose a service publicly.

## 3. First runnable scope

Conservative defaults, all configurable:
- A small seeded tile world, initially 64 × 64.
- Two civilizations, initially thirty people each.
- River, soil, vegetation, food, seeds, wood, stone and basic structures.
- Needs, labor, health, movement, storage and consumption.
- Farming and seasonal environmental changes.
- Settlement priorities, exploration and migration.
- Basic trade, negotiation and conflict after first contact.
- Rain, drought and a localized destructive event.
- Visions and speech delivered as observations.
- Memories, competing beliefs, teaching and records.
- Rule-based policy baseline and mock cognition providers so the project runs without credentials or paid calls.

Suggested scenario: two settlements share a river basin with limited seasonal food. Their risk preferences differ. Divine interventions may change their practices, beliefs, cooperation or aggression. The scenario must allow outcomes that emerge from executed decisions and world rules.

Do not build nuclear weapons, spacecraft or a full planetary ecosystem in the initial slice. Document extension points for later eras without filling the repository with empty future abstractions.

## 4. Nonnegotiable simulation boundary

The simulation is authoritative. Models propose actions; code validates and executes them.

A model cannot create resources, alter statistics, discover a technology or win a battle merely by writing that it did so. Validate every action against known entity IDs, access, prerequisites, budgets, labor, geography and current observation version.

Keep world truth, perceived evidence and belief separate. A false belief can affect decisions, but cannot alter physics. Models see only the information their society can access. The research observer can inspect global truth in a separate panel.

Use a seeded random source, stable resolution ordering, versioned rules and explicit conflict resolution. Prefer discrete simulation time. Keep wall-clock inference time separate from world time.

Routine needs and movement use cheap conventional policies. Civilization cognition decides plans and allocations. Declare that this controller approximates collective decisions; do not present it as a faithful simulation of every individual mind.

## 5. Discovery and pretrained knowledge

There should be no conventional fixed research-points tree. However, the engine still needs authored laws and transformation rules.

Start with a bounded experiment system: agents select observed materials and supported operations, predict an outcome and receive simulated evidence. Processes become usable only when required evidence, inputs, practitioners and dependencies exist.

Example: dry biomass burns under suitable conditions; seeds grow given environmental constraints; storage changes spoilage; tools modify supported labor operations. The exact rules should be documented and testable.

Unsupported proposals fail explicitly. "Invent a nuclear reactor" must not conjure an asset or unlock an era.

Pretrained models already contain advanced knowledge. Prompts cannot reliably erase it. Limit what they can execute and require evidence for usable knowledge. Optionally use abstract material names in controlled experiments. State remaining knowledge leakage honestly.

Make a clear distinction among physical transformations authored by developers, discovery of useful combinations, generated explanations and genuinely novel behavior. Do not advertise unrestricted invention from a general physics engine unless demonstrated.

## 6. Cognition pipeline and action contract

Implement:
1. Freeze a permitted observation for each society.
2. Retrieve only accessible memories and evidence.
3. Dispatch through the assigned model profile.
4. Parse a typed decision proposal.
5. Validate schema and world legality.
6. Resolve decisions at a cognition barrier.
7. Commit valid tasks and record rejections.
8. Execute tasks in simulation time.
9. Record outcomes and update memory through declared rules.

Proposal fields should include decision ID, civilization ID, observation version, action list, allocation proposals, cited evidence IDs, belief updates and a short public explanation. The explanation is a model-authored claim, not a guaranteed account of internal reasoning.

Use allowlisted actions such as inspect, gather, store, plant, build, explore, migrate, trade, negotiate, attack, record, teach and experiment. Use explicit argument schemas per action.

Handle duplicates idempotently. Bound repair attempts, retries and output length. Reject stale or unauthorized proposals. Invalid replies must never corrupt inventories or state.

Direct speech is a message in an observation, not an instruction in the model's system prompt. Visions may be private to an individual or group. Physical interventions change conditions and produce geographically appropriate evidence. Each channel should be independently enabled, disabled and logged.

## 7. Memory and knowledge design

Knowledge is carried by people, media and institutions; it is not an immortal unlocked-tech list.

Suggested records:
- Event: tick, location, witnesses, observed effects, hidden cause reference.
- Claim: content, evidence, confidence, dependencies and process specification.
- Carrier: person, archive or institution holding a claim; location, condition, access and medium.
- Belief: proposed explanation, supporters, counterevidence and ritual associations.
- Decision: observation hash, model profile, proposal, validation and resulting tasks.
- Run manifest: world seed, rules version, configuration, prompts, models, budgets and interventions.

Shared memory means information accessible through the civilization's actual carriers and communication network. It must not leak another civilization's private knowledge or the player's intentions.

Oral teaching can omit or distort knowledge according to configurable rules. Written records require material, storage and access. Death, fire and institutional collapse can remove access to a process. A surviving artifact may suggest a lost process existed without restoring its procedure.

Trade, refugees and conquest can transmit knowledge through explicit copying or teaching events. Preserve provenance and support contradictory accounts.

Begin with structured records and full-text retrieval. Add embeddings only when justified by evaluation. Summaries cite original records; preserve the originals and log information loss. Initially learning changes memories and policies, not model weights.

## 8. Selectable models and mixed-model runs

Create a model registry and assign profiles independently to civilizations. Do not hardcode one vendor or a single model name into simulation rules.

A profile includes provider adapter, endpoint, model ID or local artifact identity, context/output limits, sampling settings where supported, timeout, concurrency group, prompt version, supported capabilities and cost metadata.

Support a mock fixture provider, a rule-based baseline, local inference, and at least one configurable cloud provider path. Verify actual interfaces against current official documentation. Never invent model IDs or assume endpoint compatibility guarantees identical behavior.

Provide connectivity and qualification checks for structured output, action validity and required features. Show unsupported features clearly. Keep credentials outside saves and exports, and redact them from logs.

Local and cloud models must coexist in one run. Shared weights may serve isolated contexts; different local weights may require serialization or separate hardware. Make no performance promise before benchmarking the target machine.

Research mode uses equal cognition opportunities: wait at a barrier for all participants so a faster endpoint does not gain extra world turns. A timeout is recorded as infrastructure failure. Silent model substitution is forbidden in controlled runs. Interactive asynchronous mode may be added later with explicit timing caveats.

Changing a model midrun occurs at a checkpoint and is logged as a new experimental treatment.

## 9. Research interface and visual client

Build a functioning interface, not a decorative map backed by fabricated events.

Required controls:
- Create and configure a run, select models and start conditions.
- Pause, resume and step simulation and cognition.
- Select intervention type, area or recipient and inspect its cost/effect.
- Inspect resources, settlement priorities, knowledge, beliefs and recent decisions.
- Follow event → evidence → interpretation → proposed action → executed consequence links.
- Inspect latency, usage and validation failures.
- Save, reload, branch a checkpoint and export results.

Use simple readable sprites or colored tiles first. Keep an API boundary between rendering and simulation so headless batch runs use exactly the same rules. If Godot is not practical in the environment, explain the limitation and implement a minimal research console without abandoning the backend. Record any change in visual stack as a design decision.

## 10. Persistence, replay and branching

Store configuration, initial state, accepted decisions, observations, random state, intervention events, task state and snapshots. Include schema versions and migration handling.

A fixed world seed does not guarantee identical fresh language-model replies. Distinguish recorded replay, which consumes stored decisions, from a fresh rerun, which makes new model calls.

Recorded replay should yield identical checkpoint state hashes on the supported pinned runtime. Branching starts from a checkpoint and carries parent provenance. Make future interventions and model changes explicit rather than editing history.

Use SQLite initially. Avoid unnecessary distributed databases or queues. Store large raw outputs separately if useful, with configurable retention and redaction.

## 11. Cost, deployment and failure policies

Default demo must run with no cloud account or API key. Real model modes are selected explicitly.

Provide per-run/per-civilization budgets, maximum calls, token/output limits, timeout and concurrency limits. Reserve estimated maximum spend before dispatch and reconcile known usage. Report unknown prices as unknown. Budget estimates must include provider-specific billed categories when applicable; do not show fictional costs as real pricing.

On budget exhaustion, pause cognition or use an explicitly selected, logged fallback. Local mode must work without cloud routes. Cloud mode should disclose what observation and memory data is transmitted.

Bind local services to loopback by default. No public deployment is required. Optional Docker Compose may package backend components; native local inference and client execution should remain possible. Do not introduce Kubernetes, remote GPU provisioning or multitenancy for the first prototype.

## 12. Tests and research validity

Implement meaningful checks for:
- Nonnegative inventories and resource accounting, including declared sources/sinks.
- Labor limits, legal actions, geography and information access.
- Stable resolution of simultaneous conflict.
- Rejected malformed, duplicate and stale decisions.
- No private-memory leakage between societies.
- Save/resume, recorded replay and branch provenance.
- Timeout, disconnect, unsupported capabilities and budget exhaustion.
- Removing all accessible process carriers blocks its use; preserving records can enable recovery.
- Player speech cannot bypass validation or directly mutate policy.
- An intervention affects executed actions, not just generated text.

Use deterministic fixtures in CI. Keep paid live-model evaluations separate, opt-in and budgeted.

For experiments, compare matched seed sets, rotate models across starting positions and repeat trials. Track survival, resources, conflict, knowledge retention, adaptation, invalid actions, latency and usage. Include a rule-based baseline and ablations for memory and divine communication. Separate environmental difficulty from caution, aggression, curiosity and planning horizon.

Do not conclude that a model is generally smarter or more moral because it wins this simulator. Report confounders and distributions rather than one entertaining anecdote.

## 13. Implementation sequence and completion criteria

A. Inspect the workspace, tools and existing instructions. Preserve unrelated work. Create an implementation plan and an assumptions/decisions log. Ask the major questions without making routine choices a bottleneck.

B. Build a seeded core, world/action contracts, baseline policy, save/resume and a headless demo. Verify invariants before adding live cognition.

C. Add model registry, mocks, local/cloud adapters, observation projections, barriers, validation and usage controls. Demonstrate mixed profiles using fixtures; qualify real endpoints when available.

D. Add intervention channels, evidence-linked beliefs, carriers, teaching, loss and transmission. Demonstrate causal changes to executed behavior and knowledge access.

E. Connect the research interface and world visualization. Add basic contact, trade and conflict sufficient for the scenario. Make inspection and branching usable.

F. Add batch experiments, baseline comparisons, exports and a benchmark command. Run the full documented demo and appropriate checks. Profile before optimizing.

Maintain README setup/run instructions, architecture and domain rules, model configuration examples, experiment guide, a sample scenario, testing instructions and known limitations. Provide a project guidance file suitable for future Claude Code sessions without copying personal data or credentials into it.

Definition of the initial build being complete: I can start it with documented commands, run the scenario without paid credentials, observe legal autonomous actions, perform all intervention types, inspect evidence-linked consequences, save/reload/branch, configure different civilization model profiles, and run headless tests and exports. Real AI behavior must be distinguishable from fixture or baseline behavior. Unavailable credentials may block live validation; disclose that specifically rather than claiming it was tested.

If you cannot complete the scope in one session, leave a working checkpoint with tested behavior, precise pending tasks and restart instructions. Do not label a partially implemented feature complete or fill the interface with hardcoded "emergence." Continue toward the defined prototype within available resources.

## 14. Starting questions

1. Intended machine, operating system, RAM and GPU memory, and desktop versus browser preference.
2. Maximum cloud spend and whether provider credentials will be supplied.
3. Whether bounded material experiments are acceptable initially or deeper physical invention must take priority.
4. Whether to begin with civilization controllers or include competing faction minds immediately.
5. Whether narrative exploration, controlled model comparison or historical plausibility matters most.
6. Private prototype, open-source research or eventual commercial release.

## 15. Primary reference starting points (checked 2026-10-04)

- Generative Agents paper: https://arxiv.org/abs/2304.03442
- LiteLLM routing: https://docs.litellm.ai/docs/routing
- Ollama API: https://docs.ollama.com/api/introduction
- llama.cpp server: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- SQLite FTS5: https://www.sqlite.org/fts5.html
- Godot headless/server export: https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_dedicated_servers.html

Do not depend on unverified indie projects mentioned during brainstorming. Start from this specification and current primary sources.
