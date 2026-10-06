# Aimpire

> **Untrained AI sandbox. Tribes evolving in an infinitely generative universe.**

A retro civilization research simulator with god-game interactions. Autonomous AI civilizations, each driven by its own selectable model (cloud or local), share one deterministic world. They gather, farm, teach, forget, trade and fight. You are a god who can send rain, drought, lightning, visions and words, but never commands. They may misunderstand you, worship you, or ignore you.

**The goal is emergence:** let the minds make their own decisions and see what kind of civilization, political order and belief arises, then trace parallels with real history. *The Great Filter* is the last challenge of the campaign, not the name of the game.

> **Status (October 2026):** foundation done, milestone **M0 "petri dish" playable** with rule minds and live models (local Ollama, OpenRouter, Anthropic). Next: experiment E0 with real models, then M1 *Seasons and a voice*. See [`docs/agents/STATUS.md`](docs/agents/STATUS.md).

## Try it

```bash
git clone https://github.com/seedfourtytwo/aimpire.git
cd aimpire/sim && uv sync
uv run aimpire run m0 --mind rule:half_full --seed 1 --years 5 --out ../runs
```

The full walkthrough, including live models and the replay player, is [Play M0](docs/guide/play-m0.md). No account or key is needed for rule minds.

## Principles

- **Rules decide; models only propose.** Code validates every order. A model cannot conjure food, technology or victory by writing about it.
- **Truth, evidence and belief are separate.** Each civilization sees only what its people perceived and passed on.
- **Deterministic and replayable.** Seeded integer maths and fixed phase order; recorded runs replay to identical state hashes and can be branched.
- **Fair comparisons.** A council barrier gives no extra turns to faster models; experiments are pre-registered and run against rule baselines.
- **Nothing emergent is scripted.** The engine provides physics and a few social primitives. It names no institution, role, belief or technology.

## Stack

| Layer | Choice |
|---|---|
| Simulation | Python 3.14, uv, integer state, counter-based random draws |
| Persistence | SQLite per run, content-addressed blobs |
| Minds | In-house adapters: mock, rule, recorded, Anthropic, OpenAI-compatible (Ollama, llama.cpp, OpenRouter); native minds trained in-house (planned) |
| Client | Static replay player today; web console at M1; PixiJS + React client later |
| CI/CD | GitHub Actions, `just check` locally equals CI |

## Documentation

Start at [`docs/index.md`](docs/index.md): a reading order for newcomers and a map of which document is authoritative for what.

- [Vision](docs/vision.md): intent, the long arc, and what is decided versus imagined
- [Roadmap](docs/plan/roadmap.md) · [Open questions](docs/plan/open-questions.md) · [Decision log](docs/plan/decision-log.md)
- [Architecture](docs/architecture/overview.md) · [ADRs](docs/adr/README.md)

Preview the docs site with `just docs-serve`.

## Contributing

Read [`CLAUDE.md`](CLAUDE.md) (it is for humans too) and [`docs/agents/workflow.md`](docs/agents/workflow.md). PR titles follow Conventional Commits.

## License

[Apache-2.0](LICENSE).
