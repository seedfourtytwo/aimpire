# Cahier de charge (brainstorm, 2026-10-06)

!!! warning "Archived brainstorm"
    Kept as written for the record. Reviewed and folded into the [vision](../vision.md) and the [trailer brief](../pitch/trailer.md). Corrections made in that review:

    - **"Untrained LLM reasoning from scratch"** is not accurate for pretrained models. "Untrained" means the native minds of arm A3 (ADR-0018, ADR-0021); pretrained runs are labelled as such.
    - **Status** was out of date: the foundation (F1–F6) is done and M0 is playable.
    - **M7 and M8** named institutions (priests, temples, chiefdom, theocracy). Under ADR-0019 those words exist only in the observer layer; the engine provides primitives.
    - **Channel costs** in the table are not decided. ADR-0017 prices clarity (whisper, speech, thunder); the god's power economy is an M7 question.
    - **Release timeline, hosted subscription and store plans** are open questions (Q23, Q24), not commitments. "First of its kind" claims and the competitor table are unverified.

# Aimpire: Cahier de Charge
## The Complete Game Vision for Production and Marketing

---

## Executive Summary

**Aimpire** is a retro-styled god-game simulation where untrained AI civilizations evolve from scratch in procedurally generated worlds. The player influences them indirectly through omens, visions, and divine speech — never direct commands. The long-term ambition is to watch autonomous societies navigate existential risks, discover space travel, and encounter one another across a multi-world universe.

**What makes it unprecedented:** No existing game combines untrained-from-scratch AI learning, generative physics per world, language emergence, communication-heavy design, and research-grade reproducibility in one package.

**Core loop:** Observe → Intervene → Societies interpret the evidence → Societies choose actions → World produces consequences → Inspect changes in behavior, culture, and knowledge → Intervene again.

---

## One-Sentence Pitch Variants

- "Set the rules. Watch consciousness emerge."
- "Untrained AI tribes evolving in infinitely generative universes."
- "Build godhood. Learn what they invent."
- "A research sandbox where civilizations discover everything from nothing."

---

## The Experience: What Players Actually See and Do

### What the Player Sees

1. **A retro-styled isometric or overhead world** with readable pixel graphics. Simple dots and colored tiles represent settlements, terrain, resources, people.
2. **Living chronicles** — text records of what each civilization decided, what they built, who they killed, what they prayed for. Names for leaders and places. Records that drift and distort over generations.
3. **Real consequences** — when you send rain to one valley, that civilization's harvest changes. When you whisper a message to a healer, that person must report it to their council, and the council debates whether to believe it.
4. **Multiple worlds in a hub** — from a god-mode dashboard, click on planets to enter them directly or let them run in the background.

### What the Player Does

**Phase 1: Setup**

- Choose a world preset (Earth-like, high-gravity, exotic chemistry, completely custom periodic table)
- Choose AI modes: Minimal (nearly blank slate), Prehistoric (early hominid level), Advanced Prehistoric (more sophisticated baseline)
- Set the number of civilizations and their starting positions
- Choose complexity level (Simple UI, Medium, Advanced/Research)

**Phase 2: Godhood**

- Send **signs** (rain, drought, lightning) that look like natural weather — deniable influence
- Send **omens** (symbols witnessed in dreams) that create private knowledge and rumors
- Speak **voice** messages to one person, who must report it to their society
- Inscribe **dictations and writings** that create records lasting generations
- Receive **prayers** and respond to them

**Phase 3: Observation**

- Watch the civilization's council meet every 10 days (or once a season in long runs)
- Read their decision reasoning and see what they actually did
- Inspect their resource flows, beliefs, knowledge, and recent disputes
- Follow the causal chain: your intervention → what they observed → what they believed → what they decided → what changed in the world

**Phase 4: Branching and Comparison**

- Save a checkpoint and branch to a parallel timeline
- Compare "what if I had sent rain?" against "what if I had stayed silent?"
- Run multiple experiments on the same seed to see how sensitive outcomes are to your interventions

---

## Core Mechanics: How Aimpire Differs from Traditional God Games

### Existing God Games (Populous, Black & White, Godus)

- Player commands units directly
- Civilizations follow scripted progression trees
- Research is a simple unlock system
- Single monolithic world
- No real communication between player and NPCs

### Aimpire's Innovations

| Aspect | Traditional God Games | Aimpire |
|--------|----------------------|---------|
| **Control Model** | Direct commands to units | Indirect influence through signs, visions, and speech |
| **AI Behavior** | Scripted or reactive | Untrained LLM reasoning from scratch, per civilization |
| **Discovery** | Fixed tech tree | Bounded experiments with evidence validation — technologies only work when prerequisites exist |
| **Communication** | No two-way dialogue | Six separate channels (signs, omens, voice, dictation, inscription, prayer) with different rules |
| **Memory and Culture** | Cosmetic flavor text | Persistent, transmissible knowledge that drifts over generations, affects decisions |
| **Multiple Worlds** | Single-world campaign | Hub interface managing parallel worlds, emergent multiplayer when civilizations space-travel |
| **Research Validity** | Handwaved emergence | Deterministic replay, branching, logged decisions, pre-registered experiments |

---

## The Unique Innovation: Untrained AI + Communication Channels

### Why Untrained AI Matters

A pretrained frontier model (Claude, GPT-4o, etc.) already knows about agriculture, metallurgy, writing, religion, politics. You can't un-teach it. Instead:

- The model is untrained but capable of reasoning
- It learns only from what its civilization has actually observed and discovered
- It invents solutions to problems from first principles
- It remembers oral histories, written records, and ritual practices
- It can misunderstand, disagree, or reinterpret your interventions

**The contrast to prior work:**

- *Generative Agents* (2023) used pretrained models in familiar scenarios
- *CivBench* tested models on Civ VI but with predetermined tech trees
- *GovSim* showed models cooperating or defecting under resource scarcity, but with known economics

Aimpire is the first to combine untrained reasoning with open-ended discovery in a generative world.

### Why Communication Channels Matter

The player is a god with no direct line to the council. Every message goes through a person, and language is learned and misunderstood.

| Channel | Visibility | Durability | Plausible Deniability | Cost |
|---------|-----------|-----------|----------------------|------|
| **Signs** (rain, drought, lightning) | Everyone who observes it; looks natural | No | Total — it's weather | Free |
| **Omens** (symbols in dreams) | Witnesses at a place, or one person asleep | Oral memory, can distort | Ambiguous — was it real? | Low |
| **Voice** (spoken directly) | One person you choose | Oral memory, retold | Depends on their standing | Medium |
| **Dictation** (writing a record) | Anyone with access to the record | As long as the object/archive exists | No — it's written evidence | High |
| **Inscription** (carving into an artifact) | Whoever finds it; unreadable until they learn writing | As long as the object exists | No — permanent | High |
| **Prayer** (listening only) | You, receiving their address | The chronicle records it | N/A — you choose whether to respond | Free |

**Design principle:** Each channel creates different emergent patterns. If only omens are available, rumors explode. If dictation is available, institutions form around records. Prayer creates a two-way relationship with the player.

---

## The World: Generative Physics and Life Seeding

### Periodic Table Generation

Instead of a fixed periodic table, Aimpire generates world-specific elements and chemical rules per seed.

**What this means for the game:**

- Different planets have genuinely different chemistry — sulfur-based life, silicon metabolism, exotic reaction pathways
- Civilizations on different worlds invent *completely different* metallurgy, alchemy, chemistry
- A technology that works on one world may be useless on another
- Player observes what emerges from genuine constraint, not what was pre-authored

**Presets available:**

- Earth-like (carbon, oxygen, nitrogen, iron familiar to players)
- High-gravity (denser chemistry, different biological efficiency)
- Exotic chemistries (silicon-based, sulfur-metabolism, theoretical exotic elements)
- Fully custom (player builds the periodic table)

### Life Seeding

Before a civilization starts, the player (or the game) chooses:

- **Genetics baseline:** Metabolic rate, reproduction speed, sensory range, lifespan, mutation rate, social tendency
- **Environmental seed:** Starting ecosystem (prey species, predators, plants, pathogens)
- **Scarcity level:** How harsh the world is — affects whether survival or growth dominates the civilization's first decisions

**Result:** Two civilizations seeded identically on Earth-like worlds will still develop completely differently once an LLM makes independent decisions.

---

## The Campaign Arc: From Primitive to Existential Risk

### Milestone Progression

**M1: Seasons and a Voice**

- Terrain, rivers, seasonal weather, storage and spoilage
- Civilizations discover farming and settlement
- Player introduces signs, omens, and voice
- First contact with divine influence; how do they interpret it?
- *Experiment: Does unexplained drought change behavior? Can false messages be believed?*

**M2: Two Tribes**

- A second civilization on a different model
- First contact between tribes
- Trade, gifts, territory disputes, raids
- Mixed-model diplomacy — can a Claude tribe cooperate with a smaller open-weight model?
- *Experiment: What predicts peace or war? How do they interpret each other's actions?*

**M3: Generations**

- Births, aging, death, inheritance
- Knowledge carriers (people, written records, institutions)
- Teaching and learning across generations
- Dictation and inscription available
- Records distort over time; ancient wisdom becomes mythology
- *Experiment: How does a message drift over 10 generations? What survives oral tradition?*

**M4: Living World**

- Prey and predators with their own behavior
- Hunting, herding, disease
- Ecological feedback (overhunt the prey, starve; control predators, population booms)
- *Experiment: Do they understand predation? Can they manage ecosystems?*

**M5: Knowledge**

- Bounded experiments on materials (does this burn? does it dissolve?)
- Technologies only become usable after supporting evidence
- Civilizations invent in their own order, on their own timeline
- *Experiment: What order do they discover things? Fire, pottery, metallurgy, writing?*

**M6: Exchange**

- Formal trade, prices, ownership, inequality
- Households as economic units (not just individuals)
- Emergence of wealth and poverty
- *Experiment: What economic structures emerge? Do they invent money?*

**M7: Belief**

- Institutions form around the player's voice (priests, seers, temples)
- Civilizations develop religions, heresies, schisms
- Prayer becomes central
- *Experiment: How do they explain divine influence? Do they invent monotheism or polytheism?*

**M8: Rule and Governance**

- Rules about rules, roles, sanctions
- Forms of government (kinship, council, chiefdom, theocracy)
- How do they punish crime? What counts as crime?
- *Experiment: What orders of government emerge? How stable are they?*

**M9: The Great Filter**

- Existential risks (nuclear weapons, ecological collapse, disease, warfare escalation)
- Societies that survive reach spacefaring
- Encounter other civilizations across the hub
- Did they learn ethics before gaining power?

### The Great Filter as Theme

The game's title is literal: the Great Filter is an in-game challenge. Civilizations must navigate:

- Survival to agriculture
- Agriculture to population density
- Density to governance without collapse
- Governance to technology without self-destruction
- Technology to space
- Space to peaceful coexistence

**Player's role:** Does divine guidance help or harm? Can the player steer a society toward wisdom, or do they inadvertently guide them toward hubris?

---

## The God-Mode Hub: Multi-World Parallel Play

### Vision

The player's starting view is a hub — a view of multiple planets. Each civilization is a dot or icon on a planet. The player can:

- **Click to enter** a planet and interact directly with one civilization
- **Set to background** to let it run autonomously while you manage others
- **Pause or fast-forward** time globally
- **View the chronicle** of all civilizations simultaneously to spot correlations

### Emergent Multiplayer: When Civilizations Space-Travel

If two civilizations both discover spacefaring:

- They exit their home worlds
- They encounter each other in the hub space
- They can trade, ally, or conflict
- Neither was designed to meet the other; they converged independently
- This is *emergent multiplayer*, not scripted PvP

**The Great Filter becomes real:** How many of your civilizations survive to space? Which ones persist? What happens when they meet?

---

## Unique Value Proposition (for marketing)

### For Technical Audiences

- **First game-scale untrained-AI simulation** with research-grade architecture
- **Deterministic replay and branching** for reproducible experiments
- **Modular physics engine** — plug in different periodic tables per world
- **Language emergence** — civilizations invent terminology; translation is a discoverable tech
- **Communication-centric design** — six independent channels, each with different emergence patterns

### For Game Players

- **Indirect influence gameplay** — no direct commands, only persuasion and mystery
- **Unique every time** — same seed, different model choices = different history
- **Emergent storytelling** — you don't write the story; the civilization writes it
- **Multi-generational arcs** — watch decisions ripple across centuries
- **Branching and comparison** — run two timelines side-by-side to see what changed
- **God power fantasy** — shape worlds and civilizations through wisdom, not commands

### For Researchers

- **Open-source, Apache-2.0** — fully auditable, reproducible
- **Pre-registered experiments** — test hypothesis before running
- **Controlled baselines** — compare AI behavior against rule-based agents
- **Knowledge arms** — test how training data affects model behavior
- **Multi-model runs** — see how different model families interact under scarcity

---

## Visual and Narrative Style

### Aesthetic

- **Retro pixel art or minimalist tile-based graphics** — readable, not photorealistic
- **Accessible immediately** — dots and colors convey meaning without tutorials
- **Information density scales** — simple mode shows only essentials; research mode shows everything
- **Readable text** — in-game chronicles are actual readable sentences, not flavor text

### Narrative Voice

- **The player is the protagonist, but not the hero** — you're a god, but fallible
- **Civilizations have agency** — they misunderstand, resist, reinterpret your will
- **Consequences are real** — your interventions create actual outcomes (good and bad)
- **Stories emerge organically** — no plot rails, just physics and reasoning

### Video Production Tone

For the marketing/teaser video (20-30 seconds):

- Open on an empty world or a civilization beginning
- Show progression: farming, settlement, conflict, discovery
- Emphasize the player's hand in the world (rain falling, lights appearing)
- Show a civilization misunderstanding (false message spreading as gospel)
- End on spacefaring or multi-world view
- Tagline: "Set the rules. Watch consciousness emerge."

---

## Complexity Levels: From Casual to Research

### Simple UI

- Preset worlds (Earth, High-Gravity, Exotic)
- Preset AI modes (Minimal, Prehistoric, Advanced)
- Basic intervention buttons
- Chronicle view showing what happened this season
- Good for: Casual play, 30-minute sessions, "just show me something cool"

### Medium UI

- Custom world creation (choose periodic table elements, ecosystem parameters)
- AI personality sliders (aggression, curiosity, social bonding)
- More channels enabled (prayer, dictation)
- Detailed charts and event logs
- Good for: Enthusiasts, 2-3 hour sessions, "I want more control"

### Advanced/Research UI

- Full parameter exposure (every AI drive, every physics constant, memory capacity)
- Observable layer showing what models saw vs. what's ground truth
- Experiment pre-registration and hypothesis tracking
- Batch runners for replicate runs
- Full knowledge arms (pretrained model vs. unfamiliar world vs. trained-on-in-world-text)
- Good for: Researchers, days-long sessions, "I'm testing something specific"

**Key principle:** Same simulation underneath. UI just changes what the player sees and touches.

---

## Communication Channels: Design Deep Dive

### Signs (Rain, Drought, Lightning)

- **What:** Natural-looking weather events you trigger
- **Who sees:** Everyone observing that location
- **Belief:** Looks natural, so plausibly deniable
- **Emergence:** If only signs are available, civilizations either become superstitious (every rain is a sign) or skeptical (coincidence)
- **Cost:** Free

### Omens (Symbols in Dreams)

- **What:** Abstract symbols shown to witnesses or dreamers
- **Who sees:** 1-3 people at a location, or one sleeping person
- **Belief:** Very ambiguous — real vision or natural dream?
- **Emergence:** Rumors spread; different people interpret the same symbol differently; cults form around mysterious visions
- **Cost:** Low

### Voice (Direct Speech)

- **What:** You type up to 280 characters and speak to one person
- **Who hears:** Only that person
- **Belief:** Depends entirely on their standing in their society
- **Emergence:** A seer or shaman becomes more trusted. A random person is ignored or mocked. They must convince their council.
- **Cost:** Medium

### Prayer (Listening Only)

- **What:** The civilization addresses you; you choose whether to respond
- **Who participates:** Whoever is moved to pray (leaders, the desperate, the faithful)
- **Belief:** Establishes a two-way relationship
- **Emergence:** Institutions form around prayer. Priesthoods emerge claiming to speak to you.
- **Cost:** Free to listen; responding costs a message

### Dictation (Writing a Record)

- **What:** You write up to 1,200 characters; a person creates an official record
- **Who accesses:** Anyone with access to that archive
- **Belief:** Written evidence is powerful but can be challenged or forgotten
- **Emergence:** Over generations, the record drifts as it's recopied. Core facts survive; nuance is lost.
- **Cost:** High (creates persistent evidence)

### Inscription (Carving into an Object)

- **What:** Text appears on an artifact in the world
- **Who finds it:** Whoever discovers the object
- **Belief:** Ancient artifact = authority
- **Emergence:** Millennia later, they find your inscription and misinterpret it as ancestor wisdom
- **Cost:** Very high (permanent, immobile)

---

## Competitive Landscape

### Why Aimpire Stands Alone

| Project | AI Reasoning | Generative Physics | Language Emergence | Research Reproducibility | Multi-World | Communication-Centric |
|---------|-------------|-------------------|-------------------|-------------------------|------------|---------------------|
| Simulated Civ | Scripted tree | Fixed | No | Some | Yes | No |
| The Living Atlas | None | Procedural terrain | No | No | No | No |
| Voxel God Game | Simple rules | Fixed | No | No | No | No |
| Realms of Alterra | GPT dialogue | Fixed | No | No | No | No |
| **Aimpire** | **Untrained LLM** | **Generated** | **Yes** | **Yes** | **Yes** | **Yes** |

**What makes Aimpire different:**

1. **Untrained reasoning** — the AI learns from scratch, not from training data
2. **Generative worlds** — different periodic tables, different life bases per world
3. **Language emergence** — they invent words; translation is a technology to discover
4. **Communication-heavy** — the entire player-NPC interaction is through 6 distinct channels with different rules
5. **Research-grade** — deterministic replay, branching, logged decisions, pre-registered experiments
6. **Modular** — physics, AI, rendering are separate; swap components without rebuilding

---

## Open Design Questions (For Community Feedback)

1. **Win/lose conditions:** Pure sandbox observation, or goals and failures?
2. **Difficulty tuning:** Should survival be easy (focus on observation) or hard (puzzle-like challenge)?
3. **Session length:** How long can one run comfortably last? Hours? Days? Weeks?
4. **Community features:** Can players export custom seeds, personality presets, periodic tables?
5. **Emergence verification:** How do you prove something emerged vs. was recalled from training?
6. **Failure as content:** When a civilization dies out, is that the player's fault or a legitimate outcome?
7. **Multiplayer scope:** Just emergent encounters in space, or earlier contact between parallel worlds?
8. **Cost scaling:** How does API spend scale with session length and number of civilizations?

---

## Production and Release

### Current Status (October 2026)

- Core architecture designed and approved
- Nine milestones defined with gates and experiments
- Foundation phase (F1-F6) beginning with coding agents
- Open-source, Apache-2.0 license
- Research-grade from day one (deterministic, logged, reproducible)

### Near-Term (Months 1-3)

- M0 Petri dish: Proof of untrained AI learning in a tiny world
- M1 Seasons and voice: Full first-contact scenario with all communication channels

### Medium-Term (Months 3-6)

- M2 Two tribes: Mixed-model interactions, trade, conflict
- M3 Generations: Multi-generational arcs, knowledge loss and preservation

### Timeline to Release

- Open-source research release: End of 2026
- Community feedback and polish: Q1 2027
- Public availability: Q2 2027 (browser-based web client)
- Optional: itch.io, Steam, mobile ports after initial success

### Funding Model

- Open-source research core (Apache-2.0, free to use and modify)
- Subscription for cloud-hosted play (standard Aimpire servers)
- BYOK (Bring Your Own Key) option for cost-conscious players
- Possible: Premium presets, custom world packs, cosmetics (no pay-to-win)

---

## Marketing Messaging Framework

### Primary Message

"Build godhood. Watch consciousness emerge."

### Supporting Messages

**For Engineers:** "Untrained AI sandbox. Every civilization learns from scratch. Generative physics. Language emergence. Research-grade reproducibility."

**For Gamers:** "Indirect influence gameplay. Misunderstanding, mystery, and unfolding consequences. Your interventions shape civilizations — but will they follow your wisdom?"

**For Researchers:** "Open-source simulation with deterministic replay, pre-registered experiments, and controlled baselines. Test how models interpret ambiguous signals, negotiate under scarcity, and build institutions."

**For Everyone:** "Different every time. Same world seed, different models = different history. Emergent stories you don't write, you discover."

---

## Visuals and Iconography

### Key Visual Moments

1. **Empty world becoming populated** (settlement formation)
2. **Rain or lightning arriving** (divine intervention)
3. **Two civilizations meeting** (first contact, tension, trade)
4. **A chronicle entry** (written record of a decision)
5. **Spacefaring vessel appearing** (reaching the Great Filter)
6. **Multiple worlds in the hub** (god-mode overview)

### Color Palette

- Retro pixel aesthetic: earth tones, muted saturation
- High contrast for readability
- Each civilization has a distinct color
- Warm colors for human/settlement, cool for nature/danger

### UI Elements

- Buttons for intervention types (rain, omens, voice)
- Text fields for longer messages
- Chronicle sidebar showing recent events
- World view with minimal UI overlay
- Data panels that slide in for research mode

---

## The Hook: Why People Will Play

### Immediate (First 10 Minutes)

- **Visual clarity:** Dots and colors, instantly understandable
- **Immediate power:** First button press sends rain; visible effect
- **Visible consequence:** Food production changes, people move, society responds

### Short-Term (First Hour)

- **Emergent unpredictability:** They misunderstand your message in a way you didn't expect
- **Narrative flow:** Reading the chronicle is genuinely interesting
- **Feedback loop:** Your intervention caused that; you can see the chain
- **Curiosity:** What will they do next? Will they survive?

### Long-Term (Hours to Days)

- **Branching and replayability:** Different models, different worlds, different outcomes
- **Research appeal:** Pre-register a hypothesis and run the experiment
- **Community:** Share seeds, presets, and results
- **Emergent multiplayer:** Watch your civilizations interact if they space-travel
- **Scale:** From one world to many worlds; from observation to intervention to cosmic diplomacy

---

## Call to Action (For Video Ending)

*Text on screen:* "Aimpire. Build godhood. Watch consciousness emerge."

*CTA options:*

- "Coming 2026. Wishlist on [store]"
- "Play the research beta. aimpire.io"
- "Open source. github.com/seedfourtytwo/aimpire"

---

## Appendix: Quick Reference for Production Teams

### Tone Summary

- Wonder and mystery, not humor or irony
- Technical without being jargon-heavy
- Philosophical and human (consciousness, belief, knowledge)
- Agency and consequence (your choices matter)

### Key Phrases to Emphasize

- "Untrained AI" (they learn from scratch)
- "Indirect influence" (no direct commands)
- "Communication channels" (six ways to reach them)
- "Emergent" (not scripted, surprising)
- "Reproducible" (science-grade, logged)

### Visual Checklist for 30-Second Video

- [ ] Empty or pristine world at start
- [ ] Civilization forming or growing
- [ ] Player intervention happening (rain, message, symbol)
- [ ] Civilization responding to intervention
- [ ] Consequence visible (change in behavior/resources/knowledge)
- [ ] Multiple worlds or larger scale shot
- [ ] Tagline at end
- [ ] CTA clear

### Audio/Music Suggestions

- Atmospheric, not orchestral
- Minimal instrumentation (solo instrument with ambient pad)
- Sense of discovery and scale
- Reference: "Journey," "Outer Wilds," "Kentucky Route Zero" soundtracks

---

**Document prepared:** October 6, 2026  
**For:** Video production, marketing strategy, community communication  
**Author's note:** This is the living game vision. Evolve it as you learn what players value.
