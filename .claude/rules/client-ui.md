---
paths:
  - "client/**"
  - "sim/src/aimpire/report/**"
---

# Charts and client (loaded when touching client/ or sim reports)

Before the first edit, read `docs/agents/ui-rules.md` — the checklist `ui-auditor` reviews against.
The essentials:

- The client renders; it never computes simulation rules. Numbers come from the replay or the API.
- Integrity: lie factor ≈ 1, zero-based bars, distributions with `n` across seeds, units and the
  mind/provenance label on every chart.
- Maximum data-ink: no 3D, shadows, gradients, boxes or heavy grids; direct labels, range frames,
  small multiples, sparklines, right-aligned tabular numerals.
- Truth / evidence / belief stay visually distinct; a civilization's view never shows what it could
  not know. Observer labels (ADR-0019) are visibly the observer's.
- Colour-blind-safe palettes, never colour alone, WCAG 2.2 AA, keyboard operable, reduced motion.
