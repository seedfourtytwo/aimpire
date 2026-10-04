---
description: Check the current branch against the Definition of Done
---
Check the current branch against the Definition of Done in AGENTS.md §5.4 (canonical). For each
item report **pass** or **fail** with evidence (command output, file:line, test name):

- Tests written first, red observed, suite green; `just check` passes (run it now).
- Lint, format, types, shape limits and repo hygiene pass.
- Determinism impact declared; golden hashes unchanged or justified.
- Schema regenerated and client updated if contracts changed.
- No network in default/test paths; no secrets, large files or generated artifacts.
- Provenance labels on new output paths.
- Docstrings, domain docs, ADRs, glossary, limitations updated as relevant.
- Fresh-context review done for risky areas (`/fresh-review`).
- What was not validated is listed; `STATUS.md` updated.

Fix what you can (through the right subagent), then report what remains.
