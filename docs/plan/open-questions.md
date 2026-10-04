# Open questions for the creator

Defaults are applied until answered. Answers go into `decision-log.md`, and into ADR status changes where an ADR is affected.

| # | Question | Default until answered | Blocks |
|---|---|---|---|
| Q1 | Is **Aimpire** the product name, with "Great Filter" as the campaign theme? | Yes. The package is named `aimpire` and the CLI `aimpire`. | E1 (naming is costly to change later) |
| Q2 | Which **license**: Apache-2.0 (patent grant, recommended), MIT, or AGPL-3.0 (keeps hosted forks open)? Art and assets under CC BY 4.0? | No license file yet, which means all rights reserved | Going public |
| Q3 | Where does the **$250 credit** show up? (a) claude.ai plan or Claude Code → it pays only for development sessions. (b) Claude Console billing → it pays for in-game API calls. (c) GCP or AWS → Vertex AI or Bedrock might be used. | Treated as (a); cognition uses mock providers plus whatever key you add | E9 live qualification |
| Q4 | Will you add a **Console API key** and/or **OpenRouter key** as GitHub Environment secrets for opt-in live evals? What is the monthly cap? | None; live evals are disabled | E9 live, E15 |
| Q5 | **Accept ADRs 0002–0009?** In particular, the move from Godot to a web client (ADR-0002) | Proposed; work proceeds on them | — |
| Q6 | **Branch protection:** turn on the `main` ruleset (PR required, `ci-ok` required, squash only) now? It needs repo admin. | Recommended; settings listed in `docs/agents/workflow.md` | Multi-agent work |
| Q7 | Should **GitHub Pages** (Source: GitHub Actions) be enabled for the docs and demo site? | `pages.yml` runs on manual dispatch only until enabled | Phone demo |
| Q8 | **Historical parallels:** should the observer only *tag* analogues (ADR-0008), or should scenarios be seeded from real geographies (e.g. a Nile-like or Mesopotamia-like basin)? | Tag only, with generic geography | E15 |
| Q9 | **Local model server:** will your CPU or Ollama server be reachable (e.g. over Tailscale) for runs launched from the cloud? | Local models are laptop-only, launched by you | Optional |
| Q10 | **Accept ADR-0010** (standards and agent model routing)? Is Opus for planning/review and Sonnet for coding the right usage trade-off for your plan? | Proposed; agents follow it | — |
