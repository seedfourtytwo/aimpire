# 91 — Native minds: a small model we train ourselves

*Planning note, 2026-10-04. Decision record: ADR-0021 (Proposed). Extends ADR-0018, arm A3.*

## What the creator asked for
First tests use a regular pretrained model. Soon after, move to a small model trained by us that does not know technology or history and has to figure things out. The creator finds this interesting in itself as an experiment.

## Is it complicated?
Less than it sounds, because the model can be small and its world is small.
- **Size.** A model of 10–30 million parameters writes fluent simple language when its training text is simple (TinyStories, Eldan and Li 2023). That trains in hours on one consumer GPU, such as the creator's RTX 2070 Super (8 GB), or a rented cloud GPU for a few dollars.
- **Format.** Small models are bad at producing exact JSON. We don't rely on them to: the reply is forced through a **grammar** at decoding time (llama.cpp GBNF grammars, served through the existing OpenAI-compatible adapter). Every reply is then a valid form, and the experiment measures *decisions*, not typing.
- **The hard part is the text, not the training.** What the model reads decides what it knows, so the corpus is the real design work.

## The one rule that matters: no knowledge may leak in through the corpus
If a frontier model writes the training stories, it smuggles in its concepts ("put seeds in the ground and wait"), even when the words are simple. A word list catches words, not ideas. So:
- **The corpus is generated, not written by an LLM.** It comes from templates and from the simulation itself: rule-baseline runs narrated by a deterministic narrator ("Ka walked to the river place. Ka found little food. The children were hungry.").
- **Closed vocabulary.** A published, versioned list of roughly 1,000–2,000 words: body, kin, hunger, weather, animals, plants, places, feelings, counting, and the actions the world allows. It contains **no** words for tools beyond the starting kit, for offices, rulers, priests, gods, money, writing or farming. A checker script refuses any corpus line with a word outside the list.
- **Concept checks.** The narrator only describes events that happened in the world, so it cannot describe an invention nobody made.
- **LLM-written text only as an ablation arm** (`A3-llm`), to measure how much it changes behaviour.

## Pipeline
1. **Vocabulary (N0).** `native/vocab/v1.txt` plus the checker; the vocabulary is itself a versioned design decision.
2. **Corpus (N1).** Sources, in order of weight:
   - a primer of template sentences about needs, kin, seasons and places;
   - narrated rule-baseline runs from M0 (and later M1);
   - council examples: an observation and a sensible reply from the baseline policies, so the model learns what a council turn looks like.
   It is deterministic from a seed, so the corpus is reproducible and its hash goes into the model card.
3. **Tokenizer and training (N2).**
   - A small byte-pair tokenizer trained on the corpus, and a small decoder-only transformer.
   - Separate `native/` uv project with PyTorch, so the simulation and CI stay light.
   - Runs on the laptop GPU or a rented GPU, never in CI.
   - The output is a model card (corpus hash, vocabulary version, parameters, training steps, loss) plus a GGUF file for llama.cpp or Ollama.
4. **Serving (N3).** llama.cpp or Ollama locally, with the reply grammar generated from the m0 contract. It is driven through `OpenAICompatProvider`, so it is just another profile at price 0.
5. **Qualification (N4).** `aimpire qualify` like any model, then the M0 experiment against random, greedy, half-full, and a frontier model in A0 and A2.
6. **Generations (N5, later).**
   - Fine-tune the next version on the chronicles and journals its own tribes wrote, after the vocabulary checker.
   - Culture then accumulates in the weights.
   - Each generation keeps its lineage in its model card.

## Expectations
- It will plan worse than a frontier model. That is the point: whatever it does, it did not remember from human history.
- It may not "think" in any deep sense at this size. If M0 shows behaviour indistinguishable from random, the next steps are a larger model (100M+), more council examples, or a longer context. That decision is made on data.
- The interesting comparisons are A0 versus A2 versus A3 on the same seeds: what each mind does with the same world, and which human parallels appear only where the model could not have read about them.

## Timing
- **Earlier than ADR-0018 said.** It starts **after M0**, not after M2, because the creator wants it and M0's rule-baseline runs are the first corpus.
- N0 and N1 can begin as soon as M0b exists.
- It stays off the critical path: milestones never wait for it.

## Sources
- Eldan R., Li Y. (2023). *TinyStories: How Small Can Language Models Be and Still Speak Coherent English?* arXiv:2305.07759.
- llama.cpp grammars (GBNF), for constrained decoding: https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md
- ADR-0018 (knowledge arms), ADR-0014 (experiment protocol).
