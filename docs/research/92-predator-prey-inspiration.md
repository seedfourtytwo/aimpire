# 92 — Inspiration: "Much bigger simulation, AIs learn Phalanx" (Pezzza's Work)

*Research note, 2026-10-06. Source: the video's auto-captions, supplied by the creator (about 1,000 words; no pictures). Nothing here is an ADR; every item is a proposal for the creator to accept.*

## What the video does
- Two kinds of creature, predators and prey. Each has a small neural network that is mutated when it reproduces (neuroevolution). Prey must live long enough to breed; predators must eat to breed and die if they do not.
- Version 1 (128×128, entities see only the other group): boom-and-bust cycles. Predators improve, prey collapse, predators starve, and only the best survivors breed. Each crash raises the skill of the next generation.
- Version 2 (512×512, up to 16,000 entities, rays report distance and a danger/food/neutral value): "the same simulation but bigger". No notable group behaviour. The author suspected a lack of benefit from grouping.
- Version 3 (same scale, prey fight back: 2 hits to kill a prey, 4 hits for prey to neutralise a predator): swarms, dense fronts, synchronised attacks and a sweeping search emerged. Predators eventually wiped out the prey.
- Stated limit: entities cannot communicate.

## Lessons for Aimpire
1. **Emergence needs a reason in the physics, not more scale.** Scale did nothing; one cooperation-rewarding rule did everything. For M2 onward, add physical thresholds where cooperation pays (big game needs several hunters; a lone camp cannot hold a crossing). These are physics, not institutions, so they respect ADR-0019, and they are natural Lab knobs under ADR-0020 (no outcome knobs).
2. **The author's loop is the twin run.** Observe, hypothesise a cause, change one mechanic, rerun. `aimpire lab twin` is that loop; ADR-0014's many-seed rule answers his "maybe I was unlucky".
3. **Crashes are the selection engine.** M0's collapses play this part; generations (M3) and the native-mind lineage (N5) are where it compounds.
4. **Calibration is hard on small maps.** Sweep (LAB2) before judging any result.
5. **Communication was his missing piece.** Our minds already have language and the god's voice. His limit on sight inside a crowd supports place-based knowledge.

## Proposal (not accepted): evolving fauna in M4
Animals as small evolving neural nets so that what tribes hunt adapts to being hunted. It needs integer, fixed-point weights to respect ADR-0007 and ADR-0012, and its own ADR before any work.

## Caveats
- The transcript has no visuals, and the word "phalanx" appears only in the title; the captions describe dense fronts.
- The video is about creatures, not minds with language; the lessons are about method and mechanics.
