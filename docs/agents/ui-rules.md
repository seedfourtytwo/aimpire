# UI and visualization rules

The Aimpire client is a **research instrument with a game's charm**, not a game with research
panels bolted on. These rules apply to every view, chart, table and map layer in `client/web/`.
They expand [AGENTS.md §9](https://github.com/seedfourtytwo/aimpire/blob/main/AGENTS.md). The
`ui-auditor` agent and `/ui-review` use the checklist at the bottom.

Main sources: Tufte, *The Visual Display of Quantitative Information* (2nd ed., 2001) and
*Envisioning Information* (1990); Shneiderman (1996) "The Eyes Have It"; Okabe & Ito, *Color
Universal Design*; WCAG 2.2. Full list in [references](../references.md).

## 1. Graphical integrity

- **Lie factor ≈ 1.** The size of an effect in the graphic equals the size in the data. No
  truncated bar baselines; no area or radius encoding of linear quantities.
- **Line charts may use a non-zero baseline** only with a clearly labelled axis, and never when the
  point is the magnitude itself.
- **Show variation, not anecdotes.** Results across seeds show the distribution (median plus IQR band,
  or all runs as faint lines) and state `n`. A single run is labelled as a single run.
- **Context on every chart:** units, rules version, scenario, seed set, model profile(s), and the
  provenance label (`LIVE`, `RECORDED`, `FIXTURE`, `BASELINE`).
- **Same quantity, same scale** across panels that are meant to be compared.
- **Display conversion only at the edge:** authoritative integers (milli-units, permille) are
  converted for display in one formatting module, never stored back.

## 2. Data-ink

- Erase non-data ink: no 3D, drop shadows, gradients, glows, background fills, heavy borders or
  boxed chart frames. Gridlines, if any, are faint and few.
- **Direct labels** at line ends beat legends. **Range frames** (axes drawn only across the data
  range) beat full boxes.
- **Small multiples** with shared scales for comparing civilizations, seeds or models.
- **Sparklines** (word-sized trend lines) inside tables and the inspector for population, food,
  health and knowledge carriers.
- Prefer a well-set table to a chart when there are fewer than ~20 numbers.
- **Tables:** right-aligned numbers, `font-variant-numeric: tabular-nums`, consistent precision per
  column, units in the header not the cells, thin or no rules, zebra striping only if rows are wide.

## 3. Traceability (Aimpire-specific)

- Every number and event on screen opens its source: event → evidence → claim/belief →
  observation → decision → task → consequence (the Link Tracer).
- **Truth, evidence and belief are visually distinct everywhere:**
  - *truth* (observer only): solid marks, upright labels;
  - *evidence* (what a civilization perceived): outlined marks;
  - *belief* (what it concluded): dashed marks, italic labels.
- The **observer's global-truth view** is a separate, clearly titled mode. A civilization's view
  never shows anything it could not know.
- Model-authored explanations are shown as quotes attributed to the civilization, never as the
  narrator's voice.

## 4. Colour and type

- **Colour encodes meaning only.** Never decoration.
- **Categorical:** Okabe–Ito: `#E69F00` orange, `#56B4E9` sky blue, `#009E73` bluish green,
  `#F0E442` yellow, `#0072B2` blue, `#D55E00` vermillion, `#CC79A7` reddish purple, `#000000` black.
  Each civilization keeps one identity colour in every view.
- **Sequential:** viridis or cividis. **Diverging:** a colour-blind-safe diverging map with a
  neutral midpoint at a meaningful zero.
- **Never colour alone:** pair with shape, pattern, position or a label.
- **Layering and separation:** muted greys for context, saturated colour for the focus.
- **Contrast:** WCAG 2.2 AA (4.5:1 text, 3:1 large text and UI components) in light and dark themes.
- **Type:** at most two families (UI sans and a pixel/mono for the retro layer); numbers in a tabular
  face; no text below 12 px equivalent except sparkline annotations.

## 5. Interaction and layout

- **Overview first, zoom and filter, then details on demand.**
- Inspection lives in **side panels**, not modal dialogs. The map stays visible while inspecting.
- Dense but calm: align to a grid, consistent spacing scale, no decorative chrome.
- **Keyboard:** every action reachable; visible focus; documented shortcuts for pause/step/scrub.
- Respect `prefers-reduced-motion`: weather and divine effects degrade to static indicators.
- Works at 390 px wide (phone demo) with panels stacked, and at desktop widths side by side.
- **Empty and error states tell the truth:** "no data yet", "provider timed out at tick 120". Never
  placeholder events or lorem ipsum in shipped views.

## 6. The retro map

- Original pixel art only (procedural `tools/artgen` first); fixed 32-colour palette (ADR-0002).
- Integer zoom, nearest-neighbour filtering, no sub-pixel smoothing.
- Readability beats nostalgia: terrain contrast passes for colour-blind viewers; units and buildings
  have distinct silhouettes, not just colours.
- Overlays (moisture, food, ownership, belief maps) use the sequential palette with a direct-labelled
  scale, toggled explicitly, one at a time by default.
- Divine interventions and weather are visible on the map **and** logged as events with causes.

## 7. Review checklist

- [ ] Lie factor ≈ 1; bars start at zero; scales shared where compared.
- [ ] Distributions/uncertainty shown with `n`; single runs labelled as such.
- [ ] Units, rules version, scenario, seeds, profiles and provenance label present.
- [ ] No chartjunk: no 3D, shadows, gradients, boxes, heavy grids, unnecessary legends.
- [ ] Direct labels, range frames, small multiples and sparklines used where they fit.
- [ ] Tables: right-aligned tabular numerals, consistent precision, units in headers.
- [ ] Every number/event links to its source records.
- [ ] Truth / evidence / belief encodings correct; civ views leak nothing.
- [ ] Okabe–Ito / viridis palettes; never colour alone; stable civ colours.
- [ ] WCAG 2.2 AA contrast in light and dark; keyboard operable; visible focus; reduced motion.
- [ ] 390 px and desktop layouts work.
- [ ] Map: integer scaling, nearest-neighbour, original art, distinct silhouettes.
- [ ] Empty/error states truthful; no fabricated content.
