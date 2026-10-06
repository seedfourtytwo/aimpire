# Expansion ideas (brainstorm, 2026-10-06)

!!! warning "Archived brainstorm"
    Kept as written for the record. Its ideas were reviewed and folded into the [vision](../vision.md), which marks each one as decided, planned or vision. Where this page differs from the vision or an ADR, they win. In particular, the "Existing tools" recommendation (Mesa, Pymunk, Godot) was **not adopted**, and the competitor list is **unverified**.

## Marketing Video Brief: Cahier de Charge

**Duration:** 20-30 seconds

**Visual Style:** Triple-A game title quality. Highly polished, visually impactful. Realistic fake in-game footage showing the world and civilization progression.

**Audience:** Engineers and technical practitioners. Assume familiarity with LLMs, simulation, procedural generation.

**Core Narrative:** Untrained AI sandbox. Generative universe. You are a god with different levels of divinity.

**Key Concepts to Show (in visual/narrative form):**

1. **Generative universe** — different planets, different physics, procedurally generated terrain and ecosystems
2. **Untrained AI tribes evolving** — simple civilizations inventing technology, language, culture from scratch (no pre-training)
3. **Levels of complexity/divinity** — from easy simplified mode to infinite tweaking potential (philosophy → technology → physics)
4. **Parallel simulations** — multiple worlds running side-by-side, independent evolution
5. **Modular architecture** — not a monolithic game; different engines (physics, AI, rendering) working together, customizable and pluggable
6. **Player as god** — steering through indirect influence (omens, voice, philosophy), not direct commands

**Tagline variants for ending:**

- "Untrained AI sandbox. Tribes evolving in infinitely generative universes."
- "Build godhood. Watch consciousness emerge."
- "Set the rules. See what they invent."

## Philosophical Complexity and Steering Through Ideas

The core innovation is having a naive AI in a sandbox that discovers everything from scratch, with the player steering philosophically rather than mechanically.

Terror Management Theory as a concrete seed principle: introduce mortality, scarcity, existential pressure into the world rules and observe whether an unsophisticated reasoning system produces religious or mythological responses as a coping mechanism.

## Generative Physics Engine

Instead of a fixed periodic table, build a physics engine that generates element and transformation tables per world. Different worlds have genuinely different fundamental rules — all documented, all pluggable.

## Parallel Asset Generator

Run a smaller LLM in parallel that listens to game state and the civilization's emerging language. Generate or augment visual assets preventively as they're about to discover fire or metallurgy, based on their trajectory and terminology.

Assets are keyed to discovery phase or cultural narrative stage rather than hardcoded progression.

## Communication Channels as Critical Design

The existing channels (signs, omens, voice, dictation, inscription, prayer) are not flavor; they are the *entire interface* between player and civilization.

- **Signs** (rain, drought, lightning) look like natural weather. Deniable influence.
- **Omens** (symbols witnessed at a place, or shown in dreams) create private knowledge. Rumors distort the message.
- **Voice** reaches one person you choose. They must report it to their society.
- **Dictation and inscription** create records that can be copied, lost, or misunderstood over generations.
- **Prayer** is bidirectional — the civilization addresses you and you can respond.

Each channel is independently enabled/disabled and logged. Each creates different patterns of belief, rumor, and institutional response.

## Freedom as a Variable, Tweakable Through Complexity Levels

**Core principle: default to fun, optionally go deep.**

Different UI complexity levels accommodate different player investment:

- **Simple UI** — looks like a simplified mobile SimCity. Choose basic parameters: how much you intervene, which channels are available, scenario difficulty. Low cognitive load.
- **Medium UI** — unlocks more controls. Choose from presets for physics (Earth-like, high-gravity, exotic chemistry) and AI personality.
- **Advanced/Research UI** — all controls exposed. Every parameter available: periodic table tweaking, life-seed customization, civilization drives, exact resource flows, precise timing. Full observatory.

The same simulation runs under all three; the UI just changes what the player sees and what levers they have.

**Presets everywhere, tweaking everywhere.** Offer default world presets. Offer presets for AI personality and behavioral modes. Expose every parameter for custom builds.

## God Mode Hub: Managing Multiple Worlds

The landing page is a god mode universe. Multiple games running in parallel. Different civilizations, different starting conditions, different rule sets.

From the hub you can:

- Click on a planet to enter and intervene directly
- Pause a world or let it run in the background
- Your smart LLM watches all active worlds, recording events and logging progress
- Run multiple games in parallel without micromanaging each one

## Emergent Multiplayer: Spacefaring and Encounters

If a civilization reaches spacefaring, they exit their single world. At that point, multiple spacefaring civilizations can interact across the hub space.

Multiplayer emerges naturally: two species that both discovered space travel can now encounter each other, trade, ally, or conflict. Neither was designed to encounter the other; they converged on spacefaring independently. This is radically different from scripted multiplayer — it's *emergent diplomacy*.

The Great Filter becomes a real constraint: how many species survive to spacefaring? Which ones persist? What happens when they meet?

## Physics and Life Bases: Parameterizing Worlds

Start with Earth as baseline but make the periodic table and chemistry tweakable per world. Before a run starts, the player crafts life seeds specifying:

- **Chemistry basis:** Carbon-based (familiar), silicon-based (exotic), or other element-based biochemistry.
- **DNA tweaks:** Parameters that adjust the base life form. Metabolic rate, reproduction speed, sensory range, lifespan, mutation rate, social tendency.
- **Physics preset:** Which version of the periodic table and physics this seed faces.

The resulting civilization emerges from those constraints, not from instructions.

## AI Preset Configurations (No Retraining Needed)

Instead of retraining the model for each mode, offer preset initial conditions:

- **Minimal mode:** Nearly blank slate. Only the barest survival instincts (hunger, reproduction, fear). Watch what emerges from almost nothing.
- **Prehistoric mode:** Early hominid-level sentience. Hunger, thirst, fatigue, reproduction, curiosity, fear, basic memory, simple social bonding. The starting point humans had.
- **Advanced prehistoric mode:** Later hominid-level baseline. More complex social structures, better tool intuition, stronger abstract thought tendencies.

Players pick the preset when they create a civilization. The same untrained model runs with different starting constraint sets. No retraining between runs; just different initial drives and memory capacity.

## Language Emergence and Translation

The civilization develops its own language and terminology. A smart AI watches from conception and learns it.

Later, give them a **universal translator** as a discoverable technology — they invent it or find it as a cultural artifact. This becomes a major narrative milestone: they suddenly understand the player's messages, and can communicate back unambiguously.

Until they discover it, all communication is interpretation and misunderstanding. After, it becomes direct dialogue.

## Feedback Loops: Making Steering Feel Real

The player's intervention only feels impactful if they see the causal chain. Feedback at three scales:

**Individual scale:** Track a person who receives an intervention (a voice, an omen, a prayer answered). Show their chronicle over the following seasons or years.

**Aggregate scale:** Data points and charts showing effects. "You sent rain to the east → food production rose 23% → population grew → they expanded settlements."

**Active/immediate scale:** Real-time feedback that interventions are working. Sounds, visual effects, brief messages. "A vision appears to three people."

## Competitive Landscape

Existing projects in this space (as of Oct 2026):

- **Simulated Civ** — deterministic AI simulator, procedural maps, race to space
- **The Living Atlas** — procedural world + civilization observer, terrain-only generation
- **Voxel God Game** — autonomous tribes, hand-built art, player as god with hands
- **Realms of Alterra** — GPT-based NPC dialogue with procedural worlds

**What makes Aimpire unique:**

1. Untrained AI learning from scratch as first-class feature
2. Multiple parallel worlds with interconnection (emergent multiplayer)
3. Communication-heavy design (omens, prayer, visions, misunderstood)
4. Generative physics per world (different chemistry, different elements)
5. Language emergence and real-time translation
6. Research-grade architecture (deterministic replay, seed-based branching, logged decisions)
7. Modular, pluggable design (separate physics, AI, rendering engines)

No existing project combines untrained-from-scratch AI, generative physics, language emergence, and research-grade reproducibility.

## Open Design Questions (Unresolved)

1. **Win/lose conditions** — what defines success or failure? Is there a goal or pure sandbox observation?
2. **Player feedback** — how does the player verify an intervention worked? What's the causal loop?
3. **Replayability** — what makes someone want to run a second civilization?
4. **Learning curve** — how does a new player learn without drowning in options?
5. **Failure and extinction** — when a civilization fails, is that the player's fault or just an outcome?
6. **Emergence measurement** — how do you distinguish emergence from AI repeating training data?
7. **Session economics** — how does cost scale with session length?
8. **Community and sharing** — can players export custom seeds, presets, personalities?
9. **Branching and comparison** — can you run two branches side-by-side and compare outcomes?
10. **Challenge tuning** — how hard should survival be? Sandbox exploratory or puzzle-like?

## Existing Tools and Dependencies

**Agent-Based Modeling:** Mesa is a mature Python framework for agent-based modeling (Apache2 licensed), designed as the Python alternative to NetLogo. It provides spatial grids, agent schedulers, browser-based visualization, and analysis tools.

**Physics:** Pymunk is a Rust-core physics engine with Python bindings, deterministic with fixed timestep, fast enough for thousands of agents. Fully auditable and deterministic.

**Graphics and Simulation Decoupling:** Don't build physics and graphics together. Godot stays headless for the simulation core. PixiJS or Babylon.js on the web frontend reads from your sim state.

**Recommendation:** Start with Mesa plus Pymunk for the foundation. Both are mature, deterministic, Python-native, and you can swap graphics later without coupling to the physics core. Godot can consume your simulation state file independently.
