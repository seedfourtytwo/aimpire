# ADR-0011: Time, schedules and council cadence

- **Status:** Proposed
- **Date:** 2026-10-04
- **Deciders:** creator (proposed by the planning review)
- **Amends:** ADR-0008 (time section), ADR-0007 (units of rates)
- **Research:** [`80-plan-review-2026-10-04.md`](../research/80-plan-review-2026-10-04.md)

## Context
ADR-0008 set 1 tick = 1 day, 30-tick seasons, 120-tick years and a council (cognition round) every 10 ticks. ADR-0007 counts rates in permille per tick. The review found four problems:

- **An arithmetic error.** 120 ticks / 10 = **12 councils per civilization per year**, not 36. The figure 36 is the count for the default three-year run. Every per-year cost figure derived from it (ADR-0009, research notes 30 and 70) is three times too high.
- **Slow rates cannot be written.** At 120 ticks a year, any yearly rate under 12% is below 1 permille per tick. Births, deaths, decay of records and most demographic rates fall in that range.
- **Generations are invisible.** With realistic life histories a generation is thousands of ticks, and a 6,000-tick run shows two.
- **The long campaign is unaffordable** if every civilization holds a council every 10 ticks for centuries.

## Decision

### 1. The calendar is data
- `rules/<version>/calendar.yaml` holds `ticks_per_season` (default 30) and `seasons_per_year` (default 4).
- Simulation code reads them through `aimpire.sim.calendar.Calendar`. No literal `30` or `120` appears in `sim/` outside tests.
- A tick is the base step. Prose may call it a day, but it is a game day: with 120 ticks a year one tick stands for about three calendar days. Any rule calibrated from a real daily quantity must state its conversion in a comment.

### 2. Rates are written with their period and applied exactly
- Rules data states every rate as `{ppm: N, per: year | season | tick}`. The rate is linear (not compounded) over the stated period.
- The loader turns each rate into `(ppm, per_ticks)`. It is applied with the carried-remainder helper from ADR-0012, so no rate is ever rounded to zero.
- Per-tick permille constants are not allowed in rules files. The figures in research note 50 (for example spoilage of 20 permille per tick) are converted when `rules/v1` is authored.

### 3. Systems declare a cadence
- Every system registers `cadence: tick | season | year`. The scheduler runs it on the matching boundary.
- Life events (birth, aging, death by age, pairing) run at `season` cadence. Their probabilities are stated per year and drawn in ppm.

### 4. Life history is compressed, the calendar is not
- Target: one generation is 12 to 15 game years, so that a play session and an affordable experiment both show turnover.
- The method is the one colony games use: shorten childhood and the reproductive span, keep seasons and years as they are.
- The actual parameters are set in the Generations milestone (M3) with their own validation tests. This ADR fixes only the principle and the target.

### 5. Council cadence is a scenario setting
- `council.every_ticks`: default **10** for scenarios of five game years or less, where conversation matters; default **30** (one per season) for longer scenarios.
- `council.triggers`: a list of events that call one extra council for the affected civilization at the next tick boundary. Version 1: `SETTLEMENT_ATTACKED`, `MESSAGE_RECEIVED`, `VOICE_REPORTED`, `FAMINE`, and from M3 `LEADER_DIED`.
- `council.max_triggered_per_year`: default 4, identical for every civilization in a run. Triggered councils are logged with their trigger and count against the same budget.
- Between councils the standing policy and unfinished tasks continue (ADR-0013).

### 6. Fast-forward is an input
- `advance(n_ticks, councils=false)` runs the world on standing policy only. It is written to the inputs log, so recorded replay reproduces it.

### 7. Errata recorded here
- ADR-0008 "36 rounds per civilization per year" should read 12.
- ADR-0009 "one simulated year is about 72 calls" should read 24 for two civilizations at a 10-tick cadence. The dollar figures scale down by three.

## Alternatives considered
- **Per-tick ppm constants in rules.** Simple, but every constant silently changes meaning if the calendar changes.
- **A 365-day year.** Realistic, but three times slower for the same game time and still no generations in a session.
- **Purely event-driven councils.** Cheapest, but unbounded and hard to keep fair between models.
- **A variable tick length by era.** Deferred. Writing rates with their period keeps that door open.

## Consequences
- The rules loader is slightly more complex and each rate-driven quantity stores a carry.
- Every experiment report must state its cadence and trigger settings, because they change how often a model gets to act.
- Seasonal cadence cuts model calls by two thirds on long runs.
- Revisit if triggered councils dominate call counts, or if seasonal cadence proves too coarse for two-tribe diplomacy.

## References
- Review section "Blind spots and risks", rows 1 and 7.
- Research notes on time compression in colony games and archaeological models, summarised in the review.
