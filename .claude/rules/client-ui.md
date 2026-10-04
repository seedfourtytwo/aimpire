---
paths:
  - "client/**"
---

# Client rules (loaded when touching the web client)

Before the first edit in a session, read `docs/agents/ui-rules.md` — it is the checklist the
`ui-auditor` will review against. The essentials:

- The client renders; it never computes simulation rules. Numbers come from the API or a replay bundle.
- Tufte integrity: lie factor ≈ 1, zero-based bars, distributions with `n` across seeds, units and
  provenance labels on every chart.
- Maximum data-ink: no 3D, shadows, gradients, boxes or heavy grids; direct labels, range frames,
  small multiples, sparklines, right-aligned tabular numerals.
- Truth (solid) / evidence (outlined) / belief (dashed, italic) encodings; civ views never leak truth.
- Okabe–Ito categorical and viridis/cividis sequential palettes; never colour alone; WCAG 2.2 AA;
  keyboard operable; `prefers-reduced-motion` respected; works at 390 px.
- `src/contract/` is generated from `schema/` — never hand-edit.
- Original pixel art only, integer scaling, nearest-neighbour.
