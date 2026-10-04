# Task template: the issue is the spec

Copy this into every implementing issue. An agent should be able to do the work from the issue, `CLAUDE.md` and the linked ADRs alone.

```markdown
## Goal
One or two sentences: what is true when this is done.

## Backlog id and ADRs
F2b — ADR-0012 section B, ADR-0007.

## In scope
- Files to create or change, with paths.
- Interfaces: function and class signatures, exactly.

## Out of scope
- What not to touch, even if it looks related.

## Imitate
- An existing file that shows the expected style.

## Invariants touched
- Which lines of the "Non-negotiable invariants" in CLAUDE.md apply.

## Acceptance tests
- `sim/tests/acceptance/test_….py::test_…` — what it asserts.
These already exist and are marked as expected failures. Make them pass and remove the mark. Do not edit them.

## Verify
`just check`

## If something does not fit
If a test seems to contradict this issue or an ADR, stop. Do not edit the test. Say so in the pull request and wait.
```

## Notes for whoever writes the issue
- Write the acceptance tests first and merge them before opening the issue (ADR-0016).
- One issue should fit one session and one pull request under about 400 changed lines.
- Name real paths and real signatures. An agent follows what is written, not what was meant.
- State the model tier the issue is meant for.
