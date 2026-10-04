# Great Filter — condensed brief for research agents

Source: creator's handoff spec (2026-10-04). Working title "Great Filter" (project nickname: GodMode).

## Product
Retro (Populous / Black & White / early Age of Empires) overhead/isometric pixel-art world. Autonomous AI civilizations share one physical world, make decisions, form beliefs, share/lose knowledge, trade, fight. Player is a god: physical interventions (rain, drought, localized destruction), ambiguous visions, direct speech to inhabitants. Player cannot command units. Loop: observe → intervene → societies interpret → choose actions → world consequences → inspect → intervene.

## Confirmed
- Research simulator first (inspection, experiments, reproducibility).
- Many model providers incl. local models; DIFFERENT models per civilization in the SAME run.
- Physical events, visions and speech all supported.
- Knowledge carried by people/media/institutions; can spread, distort, be lost.
- Multiple societies coexist, discover, trade, fight.
- Retro readable visuals.

## Nonnegotiable
- Simulation is authoritative. Models PROPOSE typed actions; code validates & executes (entity IDs, prerequisites, labor, geography, observation version). Invalid replies never corrupt state.
- World truth vs perceived evidence vs belief kept separate; models see only what their society can access.
- Seeded RNG, stable resolution order, versioned rules, discrete ticks; wall-clock inference separate from world time.
- Research mode: cognition barrier — all civs wait so faster endpoints don't get extra turns. No silent model substitution.
- Recorded replay (stored decisions) must reproduce identical checkpoint state hashes; fresh rerun is distinct. Branching from checkpoints with provenance.
- No fixed tech tree: bounded experiment system over authored transformation rules; unsupported proposals fail explicitly.
- Default demo runs with no cloud credentials (mock + rule-based providers). Budgets, timeouts, token caps. Services bind loopback. No Kubernetes/multitenancy.

## First slice
64×64 seeded tile world, 2 civs × 30 people, river/soil/vegetation/food/seeds/wood/stone/structures, needs/labor/health/movement/storage, farming + seasons, exploration/migration, trade/negotiation/conflict after contact, rain/drought/local disaster, visions/speech as observations, memories/beliefs/teaching/records, rule baseline + mock cognition.

## Proposed (not confirmed) stack
Python authoritative backend, FastAPI + Pydantic contracts, SQLite (+FTS5), async cognition scheduler, LiteLLM-style provider adapters, Ollama / llama.cpp local, Godot/GDScript visual client. Research UI must support run config, pause/step, interventions, inspection of event→evidence→interpretation→action→consequence links, latency/usage, save/load/branch/export.

## Creator context (known)
- Primary dev machine: Ubuntu laptop, 15 GB RAM, NVIDIA RTX 2070 Super Max-Q (8 GB VRAM) in PRIME on-demand mode. Also a Windows laptop, a virtual Ubuntu server, an iPhone.
- Plans a separate CPU-only Ollama server, likely adding an RTX 3060 12 GB later; Tailscale suggested for remote access.
- Uses Claude via API for coding. Works across many repos; work is handed off per repository to agents/teams.
- Project will live in a GitHub repo (URL pending). Must support months of multi-session development (Claude Code + human).
