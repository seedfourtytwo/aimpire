---
description: Fresh-context review of the current branch against AGENTS.md
---
Delegate a review of the current branch to the `reviewer` subagent (it has not seen this work).
If anything under `client/` changed, also delegate to `ui-auditor` in parallel.

Relay the findings grouped as Blocking / Should fix / Nit with `file:line`. Do not fix anything
until the creator or the loop in `/tdd` says so; then route fixes through `implementer` and review
again.
