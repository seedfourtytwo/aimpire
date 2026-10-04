# ADR-0018: What the minds know: knowledge arms and native minds

- **Status:** Proposed
- **Date:** 2026-10-04
- **Deciders:** creator (goal from the creator, 2026-10-04; shaped by the planning review)
- **Extends:** the handoff specification, section 5 ("Discovery and pretrained knowledge")

## Context
The creator's ideal is a mind that knows how to be a person, wants to stay alive, and knows nothing of technology or history, so that whatever it builds is its own. Pretrained models are the opposite: they have read all of human history. Asked to play a stone-age tribe they are, in the creator's words, pretending to be dumb. This matters twice over:

- **Discovery.** A model that "invents" farming has remembered it.
- **Parallels.** If a tribe run by a pretrained model forms a council or a priesthood, that may be recall of history, not emergence.

What the evidence says:

- **Instructions do not erase knowledge**, and removal after training does not hold. Unlearning methods mostly hide knowledge, which light retraining brings back (Hu et al., arXiv 2406.13356).
- **Models recognise familiar scenarios** and play the textbook answer. Renaming labels alone slows them down, which shows how much rides on surface familiarity.
- **Models with a real knowledge cutoff exist**, trained only on old text: one on text up to 1913 (7 billion parameters), one up to 1930 (13 billion parameters). They show the idea works. No corpus exists from before writing, so none can be a stone-age mind.
- **Small models can learn coherent simple language from a purpose-made corpus.** TinyStories models under 10 million parameters write fluent stories from text limited to a small child's vocabulary.

## Decision

### 1. Four knowledge arms
Every run is labelled with one arm. The arm is an experimental factor, not a quality setting.

| Arm | Mind | World | Use |
|---|---|---|---|
| **A0** | pretrained model | familiar names and rules | play, demos, first experiments |
| **A1** | pretrained model told to reason only from what its people have seen | familiar | a cheap ablation; expected to be weak |
| **A2** | pretrained model | **unfamiliar**: coined names, and from M5 rules generated per seed | every claim about discovery |
| **A3** | **native mind**: a small model trained only on in-world text | any | the control for claims about emergence |

### 2. The world gates what a mind can do, in every arm
Unchanged from the specification: a mind may know anything, but it can only use a process its people have evidence for and carriers of. Knowledge in the head is not capability in the world.

### 3. The unfamiliar world (A2)
- **Names.** From M1 a per-seed mapping renames materials, creatures and places with coined words. It applies in prompt rendering and parsing only.
- **Rules.** From M5 the table of material transformations is generated per seed from a grammar of inputs, operations and conditions. Remembered chemistry is then useless or misleading, and the mind must experiment.
- **Ecology.** Growth, spoilage and yield parameters are drawn per seed within tested ranges.
- The rules loader is built to accept generated tables from the start.

### 4. Measuring what leaks
- **Recognition probe** (ADR-0014): what does the model say the scenario is?
- **Familiarity gap:** discovery speed in A0 minus A2 on matched seeds. The gap is the size of the leak.
- **Anachronism rate:** words and concepts in journals, annals and messages that the tribe's own knowledge store cannot account for, per thousand words, by arm.

### 5. Native minds (A3): a research track, never on the critical path
The aim is a small model that knows only what a person in the world could know.

- **Primer corpus.** Simple text about needs, kin, weather, animals and the actions the world allows, written in a closed vocabulary. A script checks every word against the vocabulary list, which is published. The list has no words for tools beyond the starting kit, for offices, or for worship.
- **Play transcripts.** Observations and replies from rule-baseline runs, so the model learns the reply format.
- **Its own history.** Later generations of the model are trained further on the chronicles and records its civilizations produced. Culture then accumulates in the weights as well as in the records.
- **Scale.** Tens of millions of parameters, trainable on the creator's 8 GB GPU.
- **Expectation.** A native mind will plan worse than a frontier model. That is acceptable. Its job is to show what arises without a memory of human history.
- **First step,** after M2: train one model on the primer and transcripts and put it through M0 qualification. Whether to go further is decided on that result.

### 6. What counts as emergence or a parallel
A real-world parallel is reported as **emergent** only if it appears in arm A2 or A3. A parallel seen only in A0 is reported as **possibly recalled** (ADR-0019).

## Alternatives considered
- **Role-play instructions alone** (A1 as the only measure). Cheap and unreliable; kept as an ablation.
- **Unlearning.** Does not hold, and targets facts, not a whole civilization's worth of knowledge.
- **A period-trained model** (1913 or 1930 cutoff). Far too late for a tribe, though useful as an arm for later eras.
- **Agents with no language at all** (reinforcement learning from scratch). Truly naive, but no speech, no belief and no chronicle: the things this project is about.

## Consequences
- Experiments multiply by arm. The roadmap budgets A0 and A2 on open-weight models and treats A3 as side research.
- The primer vocabulary is itself a design decision that shapes results. It must be small, published and versioned.
- Play mode stays A0 by default: it is the most fun and the cheapest.
- Revisit A3 if training a competent small model proves beyond the available hardware.

## References
- Eldan and Li, TinyStories (arXiv 2305.07759).
- Luo et al., "Pretraining Language Models on Historical Text" (arXiv 2606.02991); talkie, a model with a 1930 cutoff (The Decoder, 2026).
- Hu et al., "Unlearning or Obfuscating?" (arXiv 2406.13356).
- Barrie and Törnberg 2025; Georgousis et al. 2026 (recognition and label effects), cited in the review.
