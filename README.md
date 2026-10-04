# Aimpire

*The Great Filter* is one of the challenges civilizations must overcome in the long campaign, not the name of the game.

A retro civilization **research simulator** with god-game interactions. Autonomous AI civilizations, each driven by its own selectable model (cloud or local), share one deterministic world. They gather, farm, teach, forget, trade and fight. You are a god who can send rain, drought, lightning, visions and words, but never commands. They may misunderstand you, worship you, or ignore you.

> **Status: Phase 0 (planning).** This repo currently contains the specification, research, architecture decisions, roadmap and CI/agent scaffolding. No runnable code yet. See [`docs/agents/STATUS.md`](docs/agents/STATUS.md).

## Principles
- **The simulation is authoritative.** Models *propose* typed actions; code validates and executes them. A model cannot conjure resources, technology or victories by writing about them.
- **Truth, evidence and belief are separate.** Each civilization only sees what its people could have perceived and passed on.
- **Deterministic and replayable.** The world is seeded, uses integer maths and fixed phase order. Recorded runs replay to identical state hashes, and runs can be branched from checkpoints.
- **Fair model comparisons.** A cognition barrier means a faster endpoint gets no extra turns, and models are never silently substituted.
- **Runs with no credentials.** Mock and rule-based civilizations work out of the box. Live models are opt-in and budget-capped.

## Planned stack ([ADRs](docs/adr/README.md))
| Layer | Choice |
|---|---|
| Simulation + API | Python 3.14, uv, numpy, FastAPI, Pydantic v2 |
| Persistence | SQLite per run (WAL, FTS5), content-addressed blob store |
| Models | In-house adapters: mock, rule, recorded, Anthropic, OpenAI-compatible (Ollama, llama.cpp, OpenRouter) |
| Client | TypeScript web: PixiJS 8 map + React 19 research panels; static replay demos on GitHub Pages |
| CI/CD | GitHub Actions (SHA-pinned), golden-replay determinism gate, release-please |

## Documentation
Start at [`docs/index.md`](docs/index.md). Key pages:
- [Specification](docs/spec/original-handoff.md)
- [Architecture](docs/architecture/overview.md)
- [Roadmap](docs/plan/roadmap.md)
- [Open questions](docs/plan/open-questions.md)

Preview the docs site locally:

```bash
just docs-serve   # needs uv + just
```

## Contributing
Read [`CLAUDE.md`](CLAUDE.md) (also for humans) and [`docs/agents/workflow.md`](docs/agents/workflow.md). PR titles follow Conventional Commits.

## License
[Apache-2.0](LICENSE).
