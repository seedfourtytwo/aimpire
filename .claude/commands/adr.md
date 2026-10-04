---
description: Draft a new Proposed ADR from the template
argument-hint: <title>
---
Create a new Architecture Decision Record titled "$ARGUMENTS".

1. Find the next free number in `docs/adr/` (NNNN, zero-padded).
2. Copy `docs/adr/0000-template.md` to `docs/adr/NNNN-<kebab-title>.md` and fill it in from the current discussion. Set Status to Proposed and the date to today.
3. Verify any versions or APIs you cite against current primary docs.
4. Add a row to the table in `docs/adr/README.md` and an entry to the ADRs nav in `mkdocs.yml`.
5. Run `just docs`. Don't mark the ADR Accepted; only the creator does that.
