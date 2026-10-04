# 10 — Visual client & rendering

!!! note "Review note, 2026-10-04"
    Where this note conflicts with an ADR or with `docs/plan/roadmap.md`, they win. Epic numbers E1–E15 were replaced by F1–F6 and M0–M8. The full web client is deferred; a static replay player and a minimal console come first (ADR-0010, ADR-0015).

Author: graphics/client research lead · 2026-10-04 · Inputs: `00-brief.md`, `20-backend-data.md`, `40-cicd-workflow.md`, creator constraints of 2026-10-04 (cloud-first dev with no GPU or display, public OSS repo, research panels as important as the map, browser/phone demo is a plus).

## 1. Verified facts (2026-10-04)

| Item | Finding | Source |
|---|---|---|
| Godot | **4.7.2-stable** is the latest tag | `git ls-remote` https://github.com/godotengine/godot |
| Godot download in the sandbox | Editor zip (146 MB) and `export_templates.tpz` download from GitHub releases with HTTP 200. **godotengine.org and tuxfamily mirrors are blocked by the proxy.** | tested |
| Godot headless | `--headless --version` works. **Real rendering also works:** `xvfb-run godot --rendering-driver opengl3` (Compatibility renderer, Mesa llvmpipe) saved a correct viewport PNG. | tested; https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html |
| Godot web | Only WebGL 2 (Compatibility renderer). Single-threaded export (available since 4.3) needs **no COOP/COEP** and works on iOS. Threads and GDExtension need cross-origin isolation, which GitHub Pages cannot send without the PWA service-worker workaround. | https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_web.html, https://godotengine.org/article/progress-report-web-export-in-4-3/ |
| Godot C# on web | The docs still say C# projects "cannot be exported to the Web". Work is in progress and not in a stable release. **So GDScript only if we choose Godot.** | same doc; https://github.com/godotengine/godot-proposals/discussions/13076 |
| PixiJS | 8.22.0; `@pixi/tilemap` 5.0.2 (peer `pixi.js >=8.5`) | npm; https://pixijs.com/blog/pixi-v8-launches |
| Phaser | 4.2.1 (4.0.0 shipped 2026-04-10). It has a new render-node renderer and `TilemapGPULayer`. | npm; https://phaser.io/news/2026/05/phaser-3-vs-phaser-4 |
| Vite / React / Svelte / Solid | 8.3.2 / 19.3.0 / 5.57.1 / 1.9.15 | npm |
| Tables and charts | `@tanstack/react-table` 9.2.5, `@tanstack/react-virtual` 3.14.13, uPlot 1.6.32 | npm |
| Playwright | `@playwright/test` 1.63.0. The sandbox image ships `playwright` 1.56.1 and **Chromium 141 at `/opt/google/chrome/chrome`**. Playwright's own browser CDN is blocked, so sandbox runs must pass `executablePath`. | npm; tested |
| Headless WebGL in the sandbox | Chromium reports `WebGL 2.0`, renderer ANGLE/SwiftShader. `navigator.gpu` is false, so there is **no WebGPU headless**. | tested |
| Desktop wrappers | Tauri CLI 2.12.1, Electron 44.5.1 | npm |
| Others | Bevy 0.19.1, Defold 1.13.2, Pixelorama v1.2.3, LibreSprite v1.3, Aseprite v1.3.18.6 | GitHub tags |

## 2. Options

| Criterion | **A. Godot 4.7 (GDScript)** | **B. TS web: PixiJS 8 + React + Vite** | C. TS web: Phaser 4 + React | D. Bevy 0.19 | E. Defold | F. Terminal UI |
|---|---|---|---|---|---|---|
| Map feel (retro, sprites, particles, weather) | Excellent. TileMapLayer, iso/top-down, shaders, editor | Very good. It is a renderer; we write camera, culling and input | Very good. Has a game framework (scenes, cameras, tilemaps) | Good, but ECS boilerplate | Good | Poor |
| **Dense research panels** (virtualised tables, charts, link-tracing graphs, timeline scrubber, text search) | Weak. Control/Tree/ItemList with no data grid or chart ecosystem; everything hand-built | **Best.** DOM + TanStack Table, uPlot, virtual lists, CSS, accessibility | Same as B (the panels are DOM) | Weak (egui is usable but sparse) | Weak | OK for tables, no map |
| Headless dev in the cloud sandbox | Works: GitHub binary + Xvfb + opengl3. Editor is GUI-centric, and agents edit `.tscn` text without seeing the editor | **Native.** `vite build`, Vitest, Playwright on bundled Chromium | Native | cargo builds are slow; wasm needs extra tooling | Bob CLI exists; small community | Native |
| Visual verification by agents | Viewport → PNG under Xvfb (proven). Diffing is custom | Playwright `toHaveScreenshot` plus DOM assertions | Same | Custom | Custom | Text snapshots |
| Browser / iPhone demo | Single-threaded wasm, ~10+ MB engine, iOS works but the docs note Safari WebGL issues | Small bundle (~0.5–1 MB), any browser incl. iOS | Same | wasm, heavy | HTML5 OK | No |
| Contract with backend (JSON Schema → types) | Hand-written GDScript classes, or a custom generator | **openapi-typescript / json-schema-to-typescript, already chosen in 20-backend** | Same | serde types, a second language | Lua, untyped | Python, trivial |
| Static replay demo on GitHub Pages | Possible | Trivial | Trivial | Possible | Possible | n/a |
| Desktop app later | Native export | Tauri 2 / Electron | Same | Native | Native | Native |
| Agent fluency and contributor pool | Medium (GDScript 4 syntax drift is a known LLM failure mode) | **Highest** | High | Medium | Low | High |

Bevy and Defold are ruled out: their panel toolkits are weak and they add languages or ecosystems for no gain. Terminal UI is ruled out as the client, but a small `rich`/Textual inspector in the Python repo is fine as a dev tool. Electron vs Tauri is not decided now (see §6).

## 3. Recommendation

**Choose B: a web-native TypeScript client. PixiJS 8 renders the map, React 19 builds the panels, Vite bundles, and Playwright tests. Godot is the documented fallback for the "god-game feel" layer, not the v1 client.**

Why this beats the Godot proposal in the brief:
1. **The research UI is half the product.** That means event→evidence→interpretation→action→consequence tracing, sortable tables of hundreds of agents, charts, and a branchable timeline. These are DOM-shaped problems. In Godot each would be a custom widget. On the web they are library components.
2. **Cloud/agent development loop.** Everything (build, unit tests, real-GPU-free screenshots) runs in the existing sandbox with packages from npm. Claude Code can *see* its own output through Playwright screenshots in the same session. Godot works headlessly too (proven above), but scene and editor work is GUI-first.
3. **One contract pipeline.** Pydantic → JSON Schema → generated TS types, plus a CI drift check, as planned in 20/40. There is no second codegen target.
4. **Phone demo for free**, and GitHub Pages hosting needs no COOP/COEP because we use no `SharedArrayBuffer`.

**Pixi over Phaser** because we need a renderer, not a game framework. The simulation is authoritative in Python. The client only draws snapshots and deltas and hit-tests clicks, so Phaser's physics, scenes and loader add weight without benefit. Phaser 4 is a sound alternative if the team later wants its camera and tilemap features out of the box.

**React over Svelte/Solid** because of ecosystem depth for data panels (TanStack, virtualisation, charting wrappers) and the largest training corpus for agents. Use plain `pixi.js` mounted imperatively in one `<MapView>` component (not `@pixi/react`). This keeps the renderer framework-agnostic and avoids per-frame React reconciliation. State lives in a small store (zustand) fed by a `DataSource` interface.

### Client architecture
```
client/web/
  src/contract/        # GENERATED from schema/jsonschema (do not edit)
  src/data/            # DataSource: LiveSource (REST + WebSocket deltas) | ReplaySource (static files)
  src/model/           # pure TS: apply deltas, indexes, selectors (Vitest, no DOM)
  src/map/             # Pixi: tile layer, sprites, overlays (fog, belief maps), camera, picking
  src/panels/          # React: inspector, link tracer, tables, charts, timeline, run config
  src/test-hooks.ts    # window.__gf {ready, tick, selected, frameHash} when ?test=1
  assets/generated/    # procedural placeholder atlas + palette
```

## 4. Specific decisions

**Top-down vs isometric (v1): top-down orthogonal, 16×16 px tiles, integer zoom (1×–6×), nearest-neighbour.** Reasons: on a 64×64 grid you need exact tile picking, simple overlays (moisture, ownership, belief heatmaps) and readable inspection. Iso complicates depth sorting, picking and overlay alignment. A "3/4 view" sprite style (Populous-ish cliffs and trees drawn with height) gives most of the retro feel. Keep world→screen mapping behind `projection.ts` so a 2:1 iso projection can be added later as a pure render change.

**Pixel-art pipeline**
- **Palette:** one fixed 32-colour project palette committed as `assets/palette.hex` (an original palette, or an openly licensed one such as a Lospec CC0 palette with attribution). A CI lint fails any PNG with off-palette pixels.
- **Placeholder art is procedural:** `tools/artgen` (TypeScript, or Python/Pillow in the uv project) deterministically generates terrain, autotile edges, people (per-civ colour ramp), structures and resource icons from a seed. It emits `atlas.png` plus a **PixiJS spritesheet JSON** (TexturePacker "hash" format, which Pixi loads natively) and `tiles.json` (tile id → frame, terrain tags, animation frames). Agents can then add art by editing code, with no art tool needed. All of it is original, which avoids licensing issues in a public repo.
- **Hand-made art later:** Pixelorama (MIT, free) or LibreSprite (GPL fork, free) for contributors. Aseprite is optional (paid binary; source is EULA, not OSS). Export to the same atlas format through a packing script. Godot is not needed for any of this.
- **Tileset format:** our own `tiles.json`. Tiled `.tmj` is only needed if we hand-author maps, and we don't: worlds are seeded by the sim.

**Contracts:** `npm run gen:contract` runs `openapi-typescript` against the FastAPI OpenAPI schema (or `json-schema-to-typescript` against `schema/jsonschema`). CI fails if the generated output differs from what is committed.

**Testing in CI and in the sandbox**
- **Vitest** for `model/` (delta application must equal snapshot at tick N; uses golden replay fixtures shared with the Python golden tests).
- **Playwright** E2E against `vite preview` with `ReplaySource` and a committed tiny replay. No backend is needed for most tests. A separate job runs against the real FastAPI mock-provider backend.
- **Visual snapshots:** `?test=1` freezes the clock, disables animation and tweens, fixes DPR=1 and the viewport, and uses the bundled pixel font. Wait on `window.__gf.ready && __gf.tick===N`, then `toHaveScreenshot` with a small `maxDiffPixelRatio`. Chromium is forced to SwiftShader (`--use-angle=swiftshader`) so GPU-less CI and the sandbox render the same way. **Baselines are generated only in CI** (pinned `mcr.microsoft.com/playwright:v1.63.0-noble` image, through a `workflow_dispatch` "update-snapshots" job that commits). The sandbox's Chromium 141 is for agent self-checks, not baselines.
- Diff images are uploaded as artifacts and linked in the PR comment so humans can review on a phone.
- Also assert on the DOM and on `__gf.frameHash` (hash of the render-input state, not pixels), which is more robust than pixels.

**Static replay demo on GitHub Pages: yes.** The sim exports a replay bundle with `manifest.json` (seed, rules version, model and provider IDs, checkpoint hashes), `snapshot-0000.json.gz` plus periodic keyframes, `deltas.ndjson.gz`, `events.ndjson.gz` and `links.ndjson.gz` (the evidence→decision graph). `ReplaySource` fetches these and scrubs by jumping to the nearest keyframe and applying deltas. Pages serves gzip. Use plain `.json`/`.ndjson` and rely on HTTP compression, or decompress with `DecompressionStream`. This also gives research a shareable "experiment viewer" URL per run. Keep demo bundles under ~20 MB (64×64 world, tens of thousands of ticks is fine with deltas). Branching and live interventions remain backend-only and greyed out in static mode.

## 5. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Web client feels less "game-like" than Godot (particles, shaders, juice) | Pixi 8 filters, particle containers and custom shaders cover rain, drought tint, fire and divine light. Run a feel spike (§7). The fallback is Godot for the map only, embedded later, with panels staying web |
| Pixi perf with 4k–65k tiles and fog overlays | `@pixi/tilemap` or chunked baked `RenderTexture`s per 16×16 chunk; update only dirty chunks from deltas |
| Pixel diffs flaky across Chromium versions | Baselines only in the pinned container; SwiftShader; low tolerance; prefer `frameHash` and DOM asserts |
| iPhone Safari WebGL quirks | Pixi has a Canvas fallback for the demo. Test with WebKit in Playwright (CI only, since the sandbox lacks it) |
| Two-language repo (Py + TS) burden for agents | Generated contract, a single `just` entrypoint, separate path-filtered CI jobs (already in 40) |
| Network allowlist blocks Playwright browser downloads in the sandbox | Use preinstalled `/opt/google/chrome/chrome` through `executablePath`, set by env `GF_CHROMIUM` |
| Electron/Tauri decision churn | Defer. The web build is the product until there is a concrete desktop need |

## 6. Desktop later: Tauri 2 vs Electron
**Tauri 2** gives small installers and could spawn the Python backend as a sidecar. But it uses the system WebView (WebKitGTK on Ubuntu has weaker WebGL performance and other quirks). **Electron** ships a consistent Chromium, is heavy (~100 MB+), and has the same rendering as tests. Default to **Electron if desktop is ever needed** (rendering parity with CI Chromium matters more than size for a research tool). Reconsider Tauri if size matters. Most likely neither is needed: `uvicorn` + browser on localhost is the desktop app.

## 7. First de-risking prototype (1–2 agent sessions, all in the cloud)
1. `client/web` Vite + React + Pixi skeleton; `tools/artgen` generates a 16-px atlas (6 terrains, river autotiles, 2 civ people, hut, field).
2. A Python script writes a **fake replay bundle**: a 64×64 seeded world and 60 people random-walking for 500 ticks with farm/build events and an event→evidence→decision link chain.
3. `ReplaySource` + map (pan, zoom, click person) + inspector panel + virtualised people table + timeline scrubber + one uPlot chart (population or food per civ).
4. A rain-overlay shader effect as the "feel" check.
5. Playwright: 3 visual snapshots + DOM asserts. CI deploys to Pages. Creator opens it on the iPhone and the RTX laptop.
6. **Exit criteria:** 60 fps at 64×64 on the laptop, ≥30 fps on the iPhone, scrubbing 500 ticks <100 ms, stable snapshots over 5 CI reruns, the creator judges the feel acceptable. If the feel fails, timebox a Godot map spike (GitHub binary + Xvfb proven) that reads the same replay bundle.

## 8. ADR draft

```
# ADR-0002: Visual client stack

Status: Proposed · Date: 2026-10-04 · Deciders: creator + client lead

## Context
Python sim is authoritative (ADR-0001). Client renders state and deltas, sends
interventions, and must provide dense research panels (inspector, link tracing,
tables, charts, replay/branch timeline). Development is done mostly by Claude
Code in GPU-less, display-less Linux cloud sandboxes and GitHub Actions; the
repo is public; a browser/phone demo is desired. Godot web export cannot use C#
(docs, 4.7.2) and thread support needs COOP/COEP.

## Decision
- Web-native TypeScript client in client/web: Vite 8, React 19, PixiJS 8
  (imperative, one MapView), zustand, TanStack Table/Virtual, uPlot.
- Types generated from the backend schema; CI drift check.
- DataSource abstraction: LiveSource (REST + WebSocket deltas) and ReplaySource
  (static replay bundle) so the same UI serves live runs and GitHub Pages demos.
- v1 projection: top-down orthogonal, 16 px tiles, integer zoom, nearest
  filtering; projection isolated for a later isometric option.
- Placeholder art generated procedurally from code with a fixed palette;
  Pixi spritesheet JSON atlas; Pixelorama/LibreSprite for hand art.
- Testing: Vitest (model), Playwright E2E + visual snapshots (SwiftShader,
  baselines only from pinned Playwright container in CI).
- No desktop wrapper for now; Electron preferred over Tauri if needed.

## Consequences
+ Panels use mature libraries; agents can build and visually verify in sandbox.
+ Free static demos per experiment; works on iPhone.
- Game "juice" must be hand-built on Pixi; two languages in the repo.
- Revisit if the prototype fails the feel/perf exit criteria (fallback: Godot
  4.7 GDScript map client consuming the same replay/delta contract).

## Alternatives considered
Godot 4.7 GDScript (strong map, weak panels, GUI-first editor); Phaser 4
(unneeded game framework); Bevy, Defold (weak UI, extra ecosystems); terminal UI
(no map).
```
