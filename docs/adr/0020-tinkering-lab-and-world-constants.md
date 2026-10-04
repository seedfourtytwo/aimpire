# ADR-0020: The Tinkering Lab and world constants

- **Status:** Proposed
- **Date:** 2026-10-04
- **Deciders:** creator (+ planning session)
- **Supersedes / Superseded by:** —

## Context
The creator wants a workshop where anything can be tweaked: the world, the rules, the minds, the tribes and especially the physics ("what if gravity were slightly different?"). Today the plan has rule files of independent rates. Changing "gravity" would mean nothing, because no rate depends on anything else.

Constraints: determinism and integer state (ADR-0007, ADR-0012); time is data (ADR-0011); experiments are pre-registered (ADR-0014); no pre-baked institutions (ADR-0019); observations never leak truth (ADR-0013).

Full reasoning, laws and sources: `docs/research/90-tinkering-lab-and-world-physics.md`.

## Decision
1. **World constants.** `rules/v1/world.yaml` holds fundamental constants relative to Earth, in ppm or milli-degrees: `gravity`, `sunlight`, `rain`, `tilt`. Systems never read them directly.
2. **Derived rates.** The rules loader derives every physical rate from the constants by named scaling laws:
   - walking speed ∝ √g; carry load ∝ 1/g; walking energy ∝ g; water speed ∝ √g; tallest tree ∝ g^(−1/3); fall harm ∝ g; throw range ∝ 1/g;
   - season strength from tilt; plant growth ceiling from min(sunlight, water).
   Each law is a pure integer function (`isqrt`, integer cube root, tables; no floats, even at load time), documented with its source and its validated range. At Earth constants every law is the identity.
3. **Knob registry.** Every tunable is declared once in `aimpire.lab.knobs`, with path, type, unit, default, allowed range, validated range, layer and description. Layers: `world`, `rules`, `tribe`, `mind`, `god`, `display`. It is exported to `schema/` as JSON Schema.
4. **Variants.** A variant is a preset plus canonical overrides (`--set path=value`).
   - `world`, `rules` and `tribe` overrides enter the rules hash; `mind` and `god` overrides are recorded in the run manifest.
   - A value outside its validated range tags the run `beyond-model`.
   - Values outside the allowed range are refused.
5. **No outcome knobs.** No knob may name a personality, temperament, institution, regime, role or belief (ADR-0019).
6. **Lab operations:**
   - twin runs (paired seeds, first-divergence report);
   - sweeps (1-D and 2-D);
   - forks from a checkpoint;
   - scheduled world events (a knob change at a tick, recorded as data).
   All Lab runs are tagged `exploratory`. A Lab finding becomes evidence only through a pre-registered re-run (ADR-0014).
7. **Invariants stay on.** The Lab cannot disable the ledger, invariant checks, validation or budgets. Minds are never told the constants; they meet them as experience.
8. **Link to the unfamiliar world (ADR-0018, arm A2).** Because every rate derives from constants, an A2 world may also draw its constants per seed within validated ranges. Remembered Earth know-how then transfers less well, which strengthens discovery claims.
9. **Track.** W0 and LAB0 land with M0a, LAB1 with M0b, LAB2 with M0d, LAB3 and LAB4 with M1 (`docs/plan/roadmap.md`).

## Alternatives considered
- **Independent rates with a "gravity multiplier" applied by hand to some of them.** Rejected: arbitrary, and it hides the trade-offs that make the question interesting.
- **A full physics engine** (rigid bodies, fluids). Rejected: it breaks integer determinism, costs far more, and the questions are ecological and social, not mechanical.
- **Floats in the derivation step only.** Rejected: derived values are hashed, so `pow` differences across platforms would split hashes. Integer roots are cheap.
- **Changing knobs live in a running world.** Rejected, except as recorded world events, because replay must reproduce every run.

## Consequences
- Positive:
  - "What if" questions become fair, paired comparisons with a single difference.
  - Every rate has a documented reason.
  - The same registry drives the CLI, the reports and the future workshop page.
- Negative:
  - The loader becomes more complex.
  - Each new system must state which constants it reads, and its tests must cover a non-Earth value.
  - Scaling laws are approximations; the validated ranges and the `beyond-model` tag mitigate this.
- Revisit if a milestone needs a quantity no scaling law covers, or if derived values make the M0 baselines unstable.

## References
- `docs/research/90-tinkering-lab-and-world-physics.md`
- Kram, Domingo and Ferris 1997 (walk–run transition under reduced gravity); Greenhill 1881 (self-buckling); Farley and McMahon 1992 (energetics in reduced gravity).
- ADR-0007, ADR-0011, ADR-0012, ADR-0013, ADR-0014, ADR-0019.
