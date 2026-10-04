# Open questions for the creator

Defaults are applied until answered. Answers go into `decision-log.md`, and into ADR status changes where an ADR is affected.

| # | Question | Default until answered | Blocks |
|---|---|---|---|
| Q1 | ~~Product name~~ — **answered:** Aimpire; "Great Filter" is an in-game challenge | — | — |
| Q2 | ~~License~~ — **answered:** Apache-2.0 (code); assets CC BY 4.0 when art exists | — | — |
| Q3 | ~~$250 credit~~ — **answered:** credit funds coding sessions only; in-game AI uses direct API keys (pay as you go) or local models | — | — |
| Q4 | Will you add a **Console API key** and/or **OpenRouter key** as GitHub Environment secrets for opt-in live evals? What is the monthly cap? | None; live evals are disabled | L0 AI experiment |
| Q5 | ~~Accept ADRs~~ — **answered:** accepted; ADR-0010 (complexity ladder) amends 0002/0008 | — | — |
| Q6 | **Branch protection:** turn on the `main` ruleset (PR required, `ci-ok` required, squash only) now? It needs repo admin. | Recommended; settings listed in `docs/agents/workflow.md` | Multi-agent work |
| Q7 | Should **GitHub Pages** (Source: GitHub Actions) be enabled for the docs and demo site? | `pages.yml` runs on manual dispatch only until enabled | Phone demo |
| Q8 | **Historical parallels:** should the observer only *tag* analogues (ADR-0008), or should scenarios be seeded from real geographies (e.g. a Nile-like or Mesopotamia-like basin)? | Tag only, with generic geography | E15 |
| Q9 | **Local model server:** will your CPU or Ollama server be reachable (e.g. over Tailscale) for runs launched from the cloud? | Local models are laptop-only, launched by you | Optional |
