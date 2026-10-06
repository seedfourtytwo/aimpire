# Aimpire

> **Untrained AI sandbox. Tribes evolving in an infinitely generative universe.**

A retro civilization research simulator with god-game interactions. Autonomous AI civilizations, each driven by its own selectable model (cloud or local), share one deterministic world. You influence them through weather, visions and speech, never commands. Every consequence can be traced back to the evidence that caused it.

## Where the project stands (October 2026)

- **Foundation done.** Deterministic integer core, ledger, replay, model adapters (mock, rule, recorded, Anthropic, OpenAI-compatible for Ollama and OpenRouter), budgets, qualification and batch runner. About 470 tests, all green.
- **M0 "petri dish" is playable.** One group of 30 on a 64 × 64 map, one regrowing food, a council every 10 days. Rule minds and live models both run; a static replay player shows the result.
- **The Tinkering Lab has started:** world constants with derived physics, and twin-world comparisons.
- **Next:** experiment E0 with real models (local Ollama first), then M1, *Seasons and a voice*, where the god starts to speak.

Live status: [agents/STATUS.md](agents/STATUS.md).

## New here? Read in this order

| # | Read | Why | Time |
|---|---|---|---|
| 1 | [Vision](vision.md) | What Aimpire is for, the long arc, and what is decided versus imagined | 10 min |
| 2 | [Roadmap](plan/roadmap.md) | The build order and what each milestone must prove | 5 min |
| 3 | [Play M0](guide/play-m0.md) | Run it yourself: clone, `uv sync`, play a world with a rule mind | 15 min |
| 4 | [Architecture](architecture/overview.md) | How the simulation, minds and storage fit together | 10 min |
| 5 | [ADR index](adr/README.md) | Every binding decision, one page each | as needed |
| 6 | [Agent workflow](agents/workflow.md) and [`CLAUDE.md`](https://github.com/seedfourtytwo/aimpire/blob/main/CLAUDE.md) | How work is specified, built and reviewed; the invariants nobody may break | 10 min |

## Which document is authoritative

Each kind of fact lives in one place. When two pages disagree, the one higher in this list wins.

| Question | Source of truth |
|---|---|
| How is it built, and why? | [ADRs](adr/README.md) |
| What is built next, and what must it prove? | [Roadmap](plan/roadmap.md), then [backlog](plan/backlog.md) |
| What is the intent, and where is it going? | [Vision](vision.md) |
| What is waiting for a decision? | [Open questions](plan/open-questions.md) |
| What was decided, when, by whom? | [Decision log](plan/decision-log.md) |
| What is happening right now? | [Status](agents/STATUS.md) |
| How did we get here? | [Research notes](research/index.md) and [history](history/index.md): background only |

## Rules everyone follows

- **Rules decide; models only propose.** A model cannot create food, win a fight or invent anything by writing that it did.
- **Truth, evidence and belief are separate.** A civilization sees only what its people perceived and passed on.
- **Deterministic and replayable.** Seeded integer maths; a recorded run replays to identical state hashes.
- **Runs with no credentials.** Rule and mock minds work offline; live models are opt-in and budget-capped.
- **Nothing emergent is scripted.** The engine names no institution, role, belief or technology.
