# ADR-0021: Native mind track: start after M0, generated corpus, constrained replies

- **Status:** Accepted (creator, 2026-10-06)
- **Date:** 2026-10-04
- **Deciders:** creator (+ planning session)
- **Amends:** ADR-0018 section 5 (timing and corpus rules)

## Context
ADR-0018 made a self-trained small model (arm A3) a research track to begin after M2. The creator wants it sooner: first tests use a regular model, then quickly a model we train ourselves. Two risks decide the design. A corpus written by a frontier model would leak concepts that a word list cannot catch. And a tiny model cannot be trusted to produce valid replies. Full reasoning: `docs/research/91-native-minds.md`.

## Decision
1. **Timing.** The track starts after M0 (N0–N1 as soon as M0b exists). It never blocks a milestone.
2. **Corpus is generated, not LLM-written.**
   - It comes from templates and from narrated rule-baseline runs.
   - Every line passes a closed-vocabulary checker against a published, versioned list.
   - LLM-written text is allowed only as a labelled ablation arm (`A3-llm`).
3. **Replies are grammar-constrained.** The native mind decodes under a grammar generated from the reply contract, so every reply is a valid form. Experiments measure decisions, not formatting.
4. **Separate project.** Training code lives in `native/` (its own uv project with PyTorch). The simulation package, its tests and CI never import or run it. Training runs on the creator's GPU or a rented GPU, by hand.
5. **Serving through the existing adapter.** The trained model is exported for llama.cpp or Ollama and used through `OpenAICompatProvider` as a price-0 profile.
6. **Model card.** Every trained model records its corpus hash, vocabulary version, parameters, training steps and parent model (for generations). A run using it records the card hash in its manifest.
7. **Generations later.** A later version may be fine-tuned on its own tribes' chronicles, after the vocabulary checker.

## Alternatives considered
- **Frontier-written primer with a word filter.** Rejected: it filters words, not ideas.
- **Free-text replies with retries.** Rejected: a tiny model would fail most councils, and we would be measuring formatting.
- **Keep the ADR-0018 timing (after M2).** Rejected at the creator's request. M0 transcripts are enough to start.

## Consequences
- Positive: A3 comparisons come early; the corpus is reproducible; no new runtime dependency in the simulation.
- Negative: someone has to author the vocabulary and the templates; GPU time; the risk that a small model acts nearly at random (decided on data, see the note).
- Revisit if M0 qualification shows no difference from random at 30M parameters after more council examples.

## References
- `docs/research/91-native-minds.md`; ADR-0013, ADR-0014, ADR-0018.
- Eldan and Li 2023 (TinyStories); llama.cpp GBNF grammars.
