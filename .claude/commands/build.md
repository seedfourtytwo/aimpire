---
description: I-tier step - implement one issue whose acceptance tests already exist, then get a fresh S-tier review
argument-hint: <issue number>
---
Implement issue #$ARGUMENTS. The issue body is the spec; its acceptance tests already exist on `main`.

1. `gh issue view $ARGUMENTS`; read the ADRs it names. Branch `agent/$ARGUMENTS-<slug>` from an
   up-to-date `main`. Confirm the named acceptance tests fail (strict xfail).
2. Delegate the coding to `implementer` (Sonnet) with the issue body and test names. It writes its
   own unit/property tests first and cannot touch protected paths.
3. If it reports that a test contradicts the issue or an ADR: stop. Do not change the test. Put the
   explanation in the PR (or ask the creator) and wait.
4. When the acceptance tests pass, remove their `xfail` marks and nothing else (needs a session with
   `AIMPIRE_ALLOW_PROTECTED=1`; otherwise list the marks to remove in the PR for the creator).
5. Run `just check` and read the real output. Delegate a review to `reviewer` (Opus, fresh context);
   add `ui-auditor` if output or `client/` changed. Route fixes back through `implementer`; re-review
   until `approve`.
6. `/handoff`, then open the PR with the template filled in, the `just check` output and what was not
   validated. Merging is the creator's call.
