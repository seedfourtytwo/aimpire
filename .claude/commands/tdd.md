---
description: Run the full TDD loop for an issue (architect → test-writer → implementer → reviewer → scribe)
argument-hint: <issue number or short description>
---
Run the orchestrated TDD loop for: $ARGUMENTS

1. **Context.** Read `docs/agents/STATUS.md`, the issue (`gh issue view` if it is a number) and the
   ADRs it touches. Make sure you are on a branch `agent/<issue>-<slug>`, not `main`.
2. **Plan.** Delegate to the `architect` subagent. Check the returned plan against AGENTS.md §1–§4.
   If it changes architecture, a Proposed ADR must be part of it. For large or risky plans, show the
   plan to the creator before continuing.
3. **For each plan step, in order** (independent steps may run in parallel only if they touch
   disjoint files):
   a. **Red:** delegate to `test-writer` with the step's behaviours. Verify yourself that the tests
      fail for the expected reason (run them), then **commit the red tests**
      (`test(<scope>): …`) so any later change to them is visible in the diff.
   b. **Green:** delegate to `implementer` with the failing test names. If it reports a test is
      wrong, decide (or ask `architect`) — never let a test be weakened silently.
   c. Run the relevant `just` recipes and read the real output.
4. **Review.** Delegate to `reviewer` with the red-test commit SHA(s) (and `ui-auditor` if
   `client/` changed). Send blocking and should-fix findings back to `implementer`; re-review until
   `approve`. Push the branch only once it is green.
5. **Wrap up.** Run `just check`. Delegate STATUS/handoff/decision-log updates to `scribe`. Open the
   PR with the template filled in, listing what was not validated.
