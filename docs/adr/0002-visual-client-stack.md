# ADR-0002: Visual client stack — web (PixiJS 8 + React 19)

- **Status:** Proposed
- **Date:** 2026-10-04
- **Deciders:** creator + client lead
- **Research:** [`docs/research/10-client-rendering.md`](../research/10-client-rendering.md)

## Context
The Python simulation is authoritative. The client only renders snapshots and deltas, sends interventions, and must provide dense research panels: inspector, event→evidence→decision link tracing, tables of hundreds of agents, charts, and a replay/branch timeline. The spec suggested Godot.

New constraints (creator, 2026-10-04):
- Development happens in the cloud: Claude Code cloud sessions (Linux, no GPU, no display, network allowlist) and GitHub Actions.
- Open-source research release.
- Tone is a mix of fun god-game and historical parallels.
- A browser/phone demo is a plus.

Verified facts:
- Godot 4.7.2 runs headless in the sandbox (Xvfb + `opengl3` rendered a real frame).
- Godot web export cannot use C#, and threaded web builds need COOP/COEP headers.
- Headless Chromium in the sandbox supports WebGL 2 (SwiftShader).

## Decision
- **Web-native TypeScript client** in `client/web/`:
  - Vite 8, React 19, PixiJS 8 mounted imperatively in a single `MapView` component.
  - State in zustand.
  - TanStack Table/Virtual for tables and uPlot for charts.
- **Contract types are generated** from the backend schema (`openapi-typescript` / `json-schema-to-typescript`). CI fails on drift.
- **A `DataSource` abstraction** has two implementations:
  - `LiveSource`: REST plus WebSocket deltas against the local backend.
  - `ReplaySource`: a static replay bundle exported by the sim.

  The same UI therefore serves live runs and **static GitHub Pages demos** (playable on a phone).
- **Projection:** top-down orthogonal, 16 px tiles, integer zoom, nearest-neighbour filtering. Projection lives in `projection.ts` so isometric can be added later as a pure render change.
- **Art:** placeholder art generated procedurally from code (`tools/artgen`) with a fixed 32-colour palette, packed as a PixiJS spritesheet atlas. Hand art later with Pixelorama or LibreSprite. All art is original.
- **Testing:**
  - Vitest for the model layer.
  - Playwright E2E plus visual snapshots, rendered with SwiftShader. Baselines are generated only in the pinned Playwright container in CI.
  - A `window.__gf` test hook exposes `ready`, `tick` and `frameHash`.
- **No desktop wrapper for now.** The desktop experience is `uv run aimpire serve` plus a browser on localhost. Electron is preferred over Tauri if a wrapper is ever needed, for rendering parity with CI Chromium.

## Alternatives considered
- **Godot 4.7 (GDScript):** strongest map feel, but weak data panels that would all need hand-building, and a GUI-first editor workflow that is awkward for headless agents. Kept as the **fallback** for the map layer.
- **Phaser 4:** a full game framework the authoritative-sim design doesn't need.
- **Bevy, Defold:** weak UI tooling and an extra ecosystem.
- **Terminal UI:** has no map. A Textual/rich inspector is still fine as a developer tool.

## Consequences
- Panels use mature libraries.
- Agents can build and *see* the client in the sandbox through Playwright screenshots.
- Each experiment gets a free shareable demo URL.
- "Game juice" (rain, fire, divine light) must be hand-built with Pixi filters, shaders and particles.
- The repo has two languages, Python and TypeScript.
- **Revisit if** the first prototype fails its exit criteria:
  - 60 fps at 64×64 on the laptop
  - ≥30 fps on iPhone
  - scrubbing 500 ticks in under 100 ms
  - the creator finds the feel acceptable

  The fallback is then a Godot map client consuming the same replay/delta contract.
