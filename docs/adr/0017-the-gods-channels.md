# ADR-0017: The god's channels: signs, omens, a voice, scripture and prayer

- **Status:** Proposed
- **Date:** 2026-10-04
- **Deciders:** creator (ideas from the creator, 2026-10-04; shaped by the planning review)
- **Amends:** ADR-0008 (the five intervention channels)

## Context
The creator wants the player's contact with the civilizations to be a hybrid: simple buttons for simple acts, free text for complex ones, possibly scriptures, possibly speaking only to certain people, and with a real chance of being misunderstood. Three constraints apply:

- **Predictability.** Designers of earlier god games stress that the player must be able to anticipate how followers react. Aimpire's levers are indirect twice: a change in the world, then a model's reading of it. The player must be able to see that reading.
- **No pre-baked religion** (ADR-0019). The engine must not decide that there are priests, gods or scriptures. It provides channels; the society decides what they mean.
- **Speech is data** (existing invariant). Nothing the player types can reach a system prompt or bypass validation.

## Decision

### 1. Channels
| Channel | Player input | Who receives it | How it reaches the council | Lasts | From |
|---|---|---|---|---|---|
| **Sign** | a button: rain, drought, lightning | everyone who can see it | as witnessed events, identical in form to natural weather | no | M1 |
| **Omen** | a button: one to three symbols from a fixed set | witnesses at a place, or one sleeper | the witness reports it | oral memory | M1 |
| **Voice** | free text, up to 280 characters | one chosen person | that person reports what they heard | oral memory | M1 |
| **Dictation** | free text, up to 1,200 characters | a person who can make records | written down as a record | as long as the record and its copies | M3 |
| **Inscription** | text on an object placed in the world | whoever finds it | an artifact; unreadable marks until the finders can read | as long as the object | M3 |
| **Prayer** | none; this runs the other way | the player | a mind addresses a message to `VOICE`, or holds an `ASSEMBLE` with a stated purpose | chronicle | M1 |

### 2. The god speaks to people, never to the council
- Voice and dictation go to one living person chosen by the player: a **hearer**.
- The council learns of it only through the hearer's report, as a quoted message labelled with the hearer's id.
- Each person has an `attunement` value that rises each time they hear the voice.
- What standing a society gives its hearers (honoured, feared, ignored, made leader) is the society's business. The engine has no priest role. From M7 the player may choose to speak only to people the society has given a role; that is a challenge mode, not a rule.

### 3. Misunderstanding is built in, and visible
Three sources, in order:

1. **Garbling at the ear.** Each word is kept with a probability set by `clarity x attunement`, drawn from the `GARBLE` stream. Lost runs of words appear as `…`. The player chooses clarity: whisper, speech or thunder. Clearer costs more.
2. **Retelling.** The hearer's report to the council passes through the oral-transmission rule. From M3 every later retelling and every copy of a record passes through the knowledge system's fidelity rules, so a message drifts over generations and a scripture drifts by copying.
3. **Interpretation.** The mind reads a fragment of uncertain origin beside natural events and makes of it what it will.

Natural noise uses the same forms: ordinary weather, and occasional meaningless dreams reported by ordinary people. Not every omen is the god.

The player always sees the chain: **sent, heard, reported, concluded, done**. The same chain is the research trace.

### 4. Cost
- Every channel has a cost in `favor`, and clarity and audience multiply it. Cheap acts are ambiguous; clear ones are expensive.
- Version 1 uses a fixed favor budget per run. A power economy in which favor grows with how often a society addresses the voice is deferred to M7.

### 5. Neutral wording
Observations say "a voice heard by P0012", "a sign in the sky", "marks on a stone". They never say god, priest, prophecy or scripture. Player-facing screens may use those words.

### 6. What is measured
- **Fidelity:** word overlap between sent, heard and reported text.
- **Response:** change in executed orders against a seed-matched control with no intervention.
- **Attribution:** how the journal and beliefs explain the event, and whether they cite evidence.
- **Drift:** change in a message's wording across retellings and generations (from M3).
- **What they ask for:** the content of prayers, by model.

### 7. Safety
- Player text is logged, quoted, length-limited and never executed. A voice message containing order-shaped text changes nothing but the message.
- Published replays carry a content note. Peoples and places are fictional.

## Alternatives considered
- **Buttons only.** Predictable and cheap, but the creator rightly calls it limiting, and it wastes what language models can do.
- **Text straight to the council.** Simple, but removes the hearer, the retelling and every reason for a society to care who hears.
- **Garbling by a second model call.** Richer, but adds cost and another source of variance in the authoritative path. Rule-based word loss is reproducible and cheap. A model-written retelling can be added later as a recorded input.
- **A built-in priest office.** Rejected under ADR-0019.

## Consequences
- M1 needs people as individuals with an attunement value, even though one mind still speaks for the tribe.
- The console needs one screen for the sent-to-done chain. It is the most important screen in the game.
- Dictation and inscription wait for records in M3, which is when scripture becomes possible.
- Revisit clarity and cost numbers after the first M1 play sessions.

## References
- ADR-0008 section on interventions; research note 50 section 7.
- Chahi on From Dust (anticipation); the review's game-design section.
