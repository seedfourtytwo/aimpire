# References

Primary sources agents check against before stating versions, APIs or practices (CLAUDE.md "Working rules").
Record the URL and date checked in the ADR or PR that relies on them. Background research with
more sources: `docs/research/`.

Link check 2026-10-04: research papers, Python/backend, provider, Claude Code, AGENTS.md and GitHub
links were fetched and confirmed. Client/UI, Tufte, MADR, SemVer and similar long-standing sites
could not be fetched from the build sandbox and are unconfirmed for that date — re-check before
citing a specific version from them.

## Simulation and agents research

- Park et al. (2023), *Generative Agents: Interactive Simulacra of Human Behavior* — <https://arxiv.org/abs/2304.03442>
- Altera.AL (2024), *Project Sid: Many-agent simulations toward AI civilization* — <https://arxiv.org/abs/2411.00114>
- The original specification's reference list: [spec §15](spec/original-handoff.md)

## Backend, determinism, persistence

- Python docs — <https://docs.python.org/3/>
- uv — <https://docs.astral.sh/uv/>
- ruff rules and settings — <https://docs.astral.sh/ruff/rules/>, <https://docs.astral.sh/ruff/settings/>
- pyright configuration — <https://microsoft.github.io/pyright/#/configuration>
- pytest — <https://docs.pytest.org/>
- Hypothesis (property-based testing) — <https://hypothesis.readthedocs.io/>
- mutmut (mutation testing) — <https://mutmut.readthedocs.io/>
- Pydantic v2 — <https://pydantic.dev/docs/validation/latest/get-started/>
- FastAPI — <https://fastapi.tiangolo.com/>
- SQLite WAL and FTS5 — <https://www.sqlite.org/wal.html>, <https://www.sqlite.org/fts5.html>
- BLAKE2 in `hashlib` — <https://docs.python.org/3/library/hashlib.html#blake2>

## Model providers

- Claude API docs — <https://platform.claude.com/docs/en/api/overview>
- Ollama API — <https://docs.ollama.com/api/introduction>
- llama.cpp server — <https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md>
- OpenRouter docs — <https://openrouter.ai/docs>

## Client and UI

- PixiJS — <https://pixijs.com/>
- React — <https://react.dev/>
- Vite — <https://vite.dev/>
- Vitest — <https://vitest.dev/>
- Playwright — <https://playwright.dev/>
- uPlot — <https://github.com/leeoniya/uPlot>
- WCAG 2.2 — <https://www.w3.org/TR/WCAG22/>
- Okabe & Ito, *Color Universal Design* — <https://jfly.uni-koeln.de/color/>
- viridis colour maps — <https://cran.r-project.org/web/packages/viridis/vignettes/intro-to-viridis.html>
- Edward Tufte: *The Visual Display of Quantitative Information* (2nd ed., 2001), *Envisioning
  Information* (1990), *Visual Explanations* (1997), *Beautiful Evidence* (2006) — <https://www.edwardtufte.com/>
- Ben Shneiderman (1996), *The Eyes Have It: A Task by Data Type Taxonomy for Information
  Visualizations* — <https://doi.org/10.1109/VL.1996.545307>
- Tamara Munzner (2014), *Visualization Analysis and Design* — <https://www.cs.ubc.ca/~tmm/vadbook/>

## Workflow, CI/CD, supply chain

- Claude Code: subagents, hooks, model config, memory — <https://code.claude.com/docs/en/sub-agents>,
  <https://code.claude.com/docs/en/hooks>, <https://code.claude.com/docs/en/model-config>,
  <https://code.claude.com/docs/en/memory>
- AGENTS.md convention — <https://agents.md/>
- GitHub Actions secure-use reference (hardening) — <https://docs.github.com/en/actions/reference/security/secure-use>
- zizmor (workflow linter) — <https://docs.zizmor.sh/>
- OpenSSF Scorecard — <https://scorecard.dev/>
- Conventional Commits — <https://www.conventionalcommits.org/en/v1.0.0/>
- Semantic Versioning — <https://semver.org/>
- Keep a Changelog — <https://keepachangelog.com/en/1.1.0/>
- MADR (ADR format) — <https://adr.github.io/madr/>
- just — <https://just.systems/man/en/>
- MkDocs Material — <https://squidfunk.github.io/mkdocs-material/>

## Engineering practice

- Kent Beck, *Test-Driven Development: By Example* (2002)
- Martin Fowler, *Refactoring* (2nd ed., 2018) — <https://refactoring.com/>
- Alistair Cockburn, *Hexagonal Architecture (Ports and Adapters)* — <https://alistair.cockburn.us/hexagonal-architecture/>
- Eric Evans, *Domain-Driven Design* (2003): ubiquitous language → the "Words used here" list in `CLAUDE.md`
- Michael Nygard, *Documenting Architecture Decisions* (2011) — <https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>
