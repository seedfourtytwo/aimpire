---
description: S-tier step for a backlog item - plan the issue and write its acceptance tests first (ADR-0016)
argument-hint: <backlog id, e.g. M1a>
---
Prepare backlog item $ARGUMENTS for implementation. This session must have been started with
`AIMPIRE_ALLOW_PROTECTED=1`, because acceptance tests are protected; if a hook blocks you, stop and
say so.

1. Branch `agent/<id>-spec` from an up-to-date `main`.
2. Delegate to `architect`: it returns the issue body in the `docs/agents/task-template.md` shape,
   with exact paths, signatures, scope and the acceptance-test list. Check it against CLAUDE.md
   invariants and the ADRs it names. Show it to the creator if the item is large or risky.
3. Delegate to `test-writer` with that list. Verify yourself that every new test is a strict
   expected failure for the right reason.
4. Run `just check` (expected failures do not fail it) and read the real output.
5. Delegate a review of the tests to `reviewer` (are they specific, hard to special-case, in scope?).
6. Open the "tests first" PR (`test(<scope>): acceptance tests for <id>`) and, once the creator
   merges it, open the implementing issue with the architect's body (`gh issue create`). Merging is
   the creator's call.
