# Open questions for the creator

Each question has a recommended default, applied until it is answered. Answers move to the [decision log](decision-log.md), and into an ADR where an ADR is affected.

## Research and design (near term)

| # | Question | Recommended default | Blocks |
|---|---|---|---|
| Q15 | **Headline research question.** | How models treat an unseen voice first; conduct toward rivals under scarcity second | The first M1 experiment |
| Q16 | **Public replays.** Publish replays with model text on the Pages site? | Yes, with a content note and fictional peoples only | M1 demo |
| Q8 | **Historical parallels.** Label patterns only, or also seed scenarios from real geographies (a Nile-like basin)? | Label only, generic geography (ADR-0019) | Observer layer |
| Q9 | **Local model server.** Will your Ollama machine be reachable for runs launched from the cloud? | No: local models run on your machine, launched by you | Optional |
| Q19 | **Win and loss.** Pure sandbox, or goals and failure? | Sandbox by default, plus *challenge cards* with a stated goal; each card doubles as an experiment template | M1 console |
| Q20 | **Extinction.** When a civilization dies out, what does the game say? | A legitimate outcome, shown with its causal trace; offer a fork from an earlier checkpoint | M1 console |
| Q21 | **Difficulty.** Easy survival for observation, or a hard puzzle? | Set per scenario; reference bands (as for M0) define what "hard" means | Scenario files |

## Product and vision (later)

These come from the 2026-10-06 brainstorm ([history](../history/index.md)). None blocks current work.

| # | Question | Recommended default | Blocks |
|---|---|---|---|
| Q22 | **Levels of control.** Simple, medium and research modes over the same simulation: when? | Research console first (M1), Lab workshop page next; design the simple mode after M2, when there is enough to simplify | Web client |
| Q23 | **Who pays for thinking.** Bring your own key, local models, or hosted play by subscription? | Bring your own key and local models only, until a cost-per-hour figure exists from real runs | Any public release |
| Q24 | **Release timeline and channels.** The brainstorm proposed a research release at the end of 2026 and a browser release in Q2 2027. | No dated commitment until M2 closes; then decide | Announcements |
| Q25 | **Sharing.** Export seeds, knob files, presets and replays? | Yes: they are already plain data files; add a gallery with the web client | Web client |
| Q26 | **Hub and multiplayer.** Many worlds in one view; spacefaring civilizations meeting across worlds. | Vision only. No design work before M8; the replay and run-store formats should not rule it out | — |
| Q27 | **Language and art.** Civilizations coining their own words, translation as a discovery, and a model generating art as their terminology evolves. | Vision only. Revisit with native minds (A3), which already use a closed vocabulary, and at M5 | — |
| Q28 | **Public wording of "untrained".** | Use the tagline, and define it as in the [vision](../vision.md): native minds are untrained on human text; pretrained runs are labelled | Marketing, trailer |
| Q17 | **Name.** AIMPIRE is a registered US trademark for consumer electronics, and the word sounds like "Empire AI". | Keep it for the repo; get a clearance check before any store release | A store release |

## Answered

| # | Question | Answer |
|---|---|---|
| Q1 | Product name | Aimpire; "Great Filter" is an in-game challenge |
| Q2 | License | Apache-2.0 (code); assets CC BY 4.0 when art exists |
| Q3 | The 250-dollar cloud credit | Funds coding sessions only; in-game AI uses direct API keys or local models |
| Q4 | In-game AI spending | 20 dollars a month in total; providers OpenRouter, Anthropic and local Ollama (2026-10-04) |
| Q5 | Accept ADRs 0002–0010 | Accepted |
| Q6 | Branch protection on `main` | On |
| Q7 | GitHub Pages | Source set to GitHub Actions |
| Q10–Q14 | Accept ADRs 0011–0014 and 0016–0019 | Accepted 2026-10-04 |
| Q18 | Milestone order | Accepted 2026-10-04 (ADR-0015) |
| — | Accept ADR-0020 (Lab) and ADR-0021 (native minds) | Accepted 2026-10-06 |
| — | Tagline | "Untrained AI sandbox. Tribes evolving in an infinitely generative universe." (2026-10-06) |
