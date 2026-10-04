# Open questions for the creator

Defaults are applied until answered. Answers go into `decision-log.md`, and into ADR status changes where an ADR is affected.

## Open
| # | Question | Recommended answer | Blocks |
|---|---|---|---|
| Q10 | **Accept ADR-0011 (time) and ADR-0012 (numeric and random primitives)?** Both change every stored hash once code exists. | Accept | F2 |
| Q11 | **Accept ADR-0016 (agent guard rails)?** It asks you to push one CI job and create one GitHub environment. | Accept | G1 |
| Q12 | **Accept ADR-0013 (mind interface)?** | Accept | F5 |
| Q13 | **Accept ADR-0014 (experiment protocol)?** | Accept | F6 |
| Q14 | **Accept ADR-0017 (the god's channels), ADR-0018 (what the minds know) and ADR-0019 (emergence first)?** They turn your ideas of 2026-10-04 into rules. | Accept, or comment on what differs from your intent | M1, M5, M6 |
| Q4 | **Keys and caps.** An OpenRouter key as a hidden cloud credential, and an Anthropic Console key in the gated `live-eval` environment? What cap? | OpenRouter with a 20-dollar monthly cap for iteration; a per-run cap for Anthropic | F6 |
| Q15 | **Headline research question.** | How models treat an unseen voice; conduct toward rivals under scarcity second | First experiment |
| Q16 | **Public replays.** Publish replays with model text on the Pages site? | Yes, with a content note and fictional peoples only | M1 demo |
| Q8 | **Historical parallels:** label patterns only, or also seed scenarios from real geographies (a Nile-like basin)? | Label only, generic geography (ADR-0019) | Observer layer |
| Q9 | **Local model server:** will your Ollama machine be reachable for runs launched from the cloud? | Local models run on your machine, launched by you | Optional |
| Q17 | **Name.** AIMPIRE is a registered US trademark for consumer electronics, and the word sounds like "Empire AI". | Keep it for the repo; get a clearance check before any store release | A store release |

## Answered
| # | Question | Answer |
|---|---|---|
| Q1 | Product name | Aimpire; "Great Filter" is an in-game challenge |
| Q2 | License | Apache-2.0 (code); assets CC BY 4.0 when art exists |
| Q3 | The 250-dollar credit | Funds coding sessions only; in-game AI uses direct API keys or local models |
| Q5 | Accept ADRs 0002–0010 | Accepted |
| Q6 | Branch protection on `main` | On (see `STATUS.md`) |
| Q7 | GitHub Pages | Source set to GitHub Actions (see `STATUS.md`) |
| Q18 | Milestone order | Accepted 2026-10-04 (ADR-0015) |
