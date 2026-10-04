# 90 — The Tinkering Lab and world physics

*Planning note, 2026-10-04. Decision record: ADR-0020 (Proposed).*

## What the creator asked for

> An area with all the options, a more experimental area for tinkering, that feels like your workshop. Tweak things about the game, the settings, the AI, the tribes, and the physics. What happens if we change gravity just slightly?

So there are two pieces of work:

1. **World physics.** Define the world in detail as a small set of *fundamental constants* (gravity, sunlight, rain, tilt, …). Every rate a system uses is *derived* from them by a stated law. Without this, "change gravity" would mean nothing: the world would just be a list of unrelated rates.
2. **The Lab.** A workshop where any knob can be changed and the result compared fairly: the same world, the same seed, one difference.

## Part 1 — World physics: constants in, rates out

### The idea
Today a rule file would say "regrowth 2 % per tick" and "walking takes 3 ticks per place". These numbers are unrelated, so nothing connects gravity to anything.

Instead, `rules/v1/world.yaml` holds **fundamental constants**, expressed relative to Earth in ppm (Earth = 1 000 000). The rules loader turns them into **derived rates** with documented scaling laws. Systems read only the derived rates. Changing one constant then moves many rates together, the way real physics does, and the trade-offs appear by themselves.

### The first constants (W0)
| Constant | Unit | Earth | What it drives |
|---|---|---|---|
| `gravity` | ppm of Earth g | 1 000 000 | walking speed, carry load, walking energy, water speed, tree height, fall harm, throw range |
| `sunlight` | ppm of Earth mean | 1 000 000 | plant growth ceiling |
| `rain` | ppm of reference | 1 000 000 | moisture, plant growth, river flow |
| `tilt` | milli-degrees | 23 440 | season strength: summer and winter difference |
| `day_ticks`, `year` | already in `calendar.yaml` | — | time (ADR-0011) |

The human body is held fixed in W0 (an Earth human). A later "species" block could make body size a knob too.

### The derivation laws (with sources)
Each law is a pure integer function in the rules loader, with a docstring giving the law, its source and the range where it holds.

| Derived quantity | Law | Why | Valid range |
|---|---|---|---|
| Walking speed | ∝ √g | Walking is an inverted pendulum: the gait changes at a fixed Froude number v²/(gL). In reduced-gravity tests the walk–run switch speed fell from 1.98 m/s at 1 g to 0.97 m/s at 0.1 g, and the Froude number held near 0.45–0.56 from 1 g down to 0.4 g (Kram, Domingo and Ferris 1997). | 0.4–2 g |
| Carry load | ∝ 1/g | Muscles give a fixed force; a load weighs m·g. | 0.3–3 g |
| Energy to walk a distance | ∝ g (W0 simplification) | Most of the cost of walking is supporting and moving body weight (Farley and McMahon 1992, via the simulated reduced-gravity literature). Measured cost falls *less* than in proportion, so W0 marks this as a first approximation. | 0.5–1.5 g |
| Water speed (rivers, floods) | ∝ √g | Chézy and Manning flow: v = C√(RS), with C ∝ √g. | any |
| Tallest tree | ∝ g^(−1/3) | Greenhill (1881): a column buckles under its own weight above a critical height ∝ (E·I / ρ·g·A)^(1/3). | any |
| Harm from a fall | ∝ g | The energy of a fall is m·g·h. | any |
| Throw and spear range | ∝ 1/g | Projectile range v²/g. | 0.3–3 g |
| Season strength | ∝ sin(tilt), by an integer table | Insolation contrast. | 0–45° |
| Plant growth ceiling | ∝ min(sunlight, water) | Liebig's law of the minimum. | any |

All of this is done in integer arithmetic: `math.isqrt` for square roots, an integer cube root, and lookup tables for sines. The loader is outside `sim/`, but its outputs are integers that get hashed, so they must be bit-exact everywhere. Floats are not used, even at load time.

### Why this is fun: the trade-offs
Take gravity at 0.9 g:
- people walk **5 % slower**, so fewer places are in reach per council;
- they carry **11 % more** per trip;
- walking costs **10 % less** energy;
- rivers run **5 % slower**, so floods arrive later and linger;
- trees grow **3.6 % taller**, so a forest holds more wood.

No rule says "low gravity makes people settle". If that happens, it emerges from slower walking against richer hauls. That is exactly the kind of result ADR-0019 is after.

Above the valid range, the Lab still lets you set the knob. The run is then tagged **beyond-model** in its manifest and report, so nobody mistakes a cartoon for a prediction.

### A second use: honest discovery
The creator wants minds that do not already know technology (ADR-0018). Unfamiliar physics helps here too. In arm A2 the constants can be drawn per seed, so Earth know-how a pretrained model remembers transfers less well, and it has to find out how this world works.

## Part 2 — The Lab

### Layers of knobs
Every tunable is declared once in a **knob registry** (`aimpire.lab.knobs`). An entry holds its path, type, unit, default, *allowed* range, *validated* range, the layer it belongs to and a one-line description. The registry is exported as JSON Schema, like the mind contract, so the CLI, the reports and the future web workshop all read the same list.

| Layer | Example knobs | Changes the rules hash? |
|---|---|---|
| `world` | `world.gravity`, `world.sunlight`, `world.rain`, `world.tilt`, map size, place block size | yes |
| `rules` | regrowth seed term, spoilage, starvation threshold | yes |
| `tribe` | starting people, starting stores, camp place | yes (scenario) |
| `mind` | provider profile, temperature, knowledge arm (A0–A3), renderer (places or grid), journal length, council cadence | no; recorded in the run manifest |
| `god` | which channels are open, how often the voice is garbled | no; recorded in the run manifest |
| `display` | colours, frame rate | no; never recorded |

ADR-0019 guard: there are **no personality or institution knobs**. "Make tribe B aggressive" or "start as a chiefdom" are not knobs. Those are outcomes, not inputs.

### Variants
A **variant** is a preset plus a set of overrides, for example `m0 + {world.gravity: 950000}`.
- Its id is a hash of the canonical overrides.
- The overrides go into the run manifest and into the rules hash, so determinism and replay are unchanged. A variant replays exactly like any run.
- Knobs never change in the middle of a run, except through a scheduled **world event** (below), which is itself recorded data.

### What you can do in the Lab
1. **Twin worlds** (`aimpire lab twin`). Run the baseline and a variant on the same seeds, side by side. The report shows:
   - the **first tick where the worlds differ** and the state part that diverged first (from `diff_parts`, already built);
   - small-multiple charts of each metric, baseline in grey and variant in colour, directly labelled;
   - the paired difference with a band across seeds.
2. **Sweeps** (`aimpire lab sweep world.gravity=0.8..1.2:9 --seeds 32`). One knob over a range, or two knobs as a grid (a "phase diagram", for example gravity × rain coloured by survival). Rule and mock minds by default, so sweeps are free. Live minds only through a profile with a budget.
3. **Forks** (`aimpire lab fork <run> --at tick 1200 --set world.rain=700000`). Branch a recorded world from a checkpoint and change one thing: "what if the rains failed in year 10?" The run store already has parent and branch columns (F5e).
4. **World events.** Schedule a change partway through a run: "gravity −5 % from year 3", "a dry decade". These are recorded as events in the run, so the replay holds them.
5. **Workshop page.** It comes later, with the web client, and gives you:
   - sliders grouped by layer, with a live panel of what each change derives to ("walking −2.5 %, carry +5.3 %");
   - a run queue and a gallery of past experiments.
   Until then the CLI writes the same report as a static page.

### Exploring versus evidence
Lab runs are tagged `exploratory`. ADR-0014 still governs claims: a curious result found in the Lab must be **pre-registered and re-run** on fresh seeds before it counts. That protects us from the garden of forking paths. The Lab notebook keeps every variant tried, including the boring ones.

### What the Lab never does
- Turn off the ledger or the invariant checks. A nonsense world must still conserve food.
- Let a knob leak truth into an observation. A mind does not know gravity is 0.9; it only finds that walking is slow.
- Hardcode an outcome to make a demo look good.

## Build order (Lab track)
This runs alongside the milestones and never blocks them.

| Step | Lands with | Work |
|---|---|---|
| **W0** World constants | M0a | `rules/v1/world.yaml`, integer derivation laws, Earth gives identity, property tests (monotonic, validity flags) |
| **LAB0** Knob registry and `--set` | M0a | registry, schema export, overrides in the manifest and rules hash, beyond-model tag |
| **LAB1** Twin worlds | M0b | `aimpire lab twin`, divergence report |
| **LAB2** Sweeps | M0d | `aimpire lab sweep`, phase-diagram small multiples |
| **LAB3** Forks and world events | M1 | branching from checkpoints, scheduled knob changes as recorded events |
| **LAB4** Workshop page | M1 web console | sliders, derived-value preview, queue, gallery |
| **W1+** More physics | each milestone | each milestone names the constants it reads (M1: tilt, rain; M4: body size and metabolism; M5: material properties) |

## A prototype to play with now
A standalone page (the "Lab prototype" artifact) shows the idea before the engine exists:
- the real derivation table, live as you move the sliders;
- twin toy petri dishes with the same seed.

The dishes are **toy rules in JavaScript, not the Aimpire engine**, and the page says so. They are there to feel the workshop, not to produce findings.

## Sources
- Kram R., Domingo A., Ferris D. P. (1997). *Effect of reduced gravity on the preferred walk–run transition speed.* J. Exp. Biol. 200: 821–826. https://cob.silverchair.com/jeb/article/200/4/821/7425/Effect-of-reduced-gravity-on-the-preferred-walk
- Farley C. T., McMahon T. A. (1992). *Energetics of walking and running: insights from simulated reduced-gravity experiments.* J. Appl. Physiol. 73: 2709–2712.
- Greenhill A. G. (1881), self-buckling of a heavy column. Summary: https://en.wikipedia.org/wiki/Self-buckling
- McMahon T. A. (1973). *Size and shape in biology.* Science 179: 1201–1204 (tree proportions and elastic similarity).
