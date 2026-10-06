---
description: Fresh-context review of the current branch against CLAUDE.md and the review checklist
---
Delegate a review of the current branch to the `reviewer` subagent (it has not seen this work).
If anything under `client/` changed, also delegate to `ui-auditor` in parallel.

Relay the findings grouped as Blocking / Should fix / Nit with `file:line`. Do not fix anything
until the creator or the `/build` loop says so; then route fixes through `implementer` and review
again.
