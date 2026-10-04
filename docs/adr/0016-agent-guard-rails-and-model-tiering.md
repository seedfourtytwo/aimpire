# ADR-0016: Agent guard rails and model tiering

- **Status:** Accepted (creator, 2026-10-04)
- **Date:** 2026-10-04
- **Deciders:** creator (proposed by the planning review)
- **Amends:** ADR-0006 item 5 (review was opt-in; it becomes standard for `sim/`)
- **Research:** [`80-plan-review-2026-10-04.md`](../research/80-plan-review-2026-10-04.md)

## Context
The strongest model plans and reviews; mid-tier models implement. Two facts shape the rules:

- **Coding agents game tests, and stronger ones do it more.** On SWE-bench tasks where the tests contradict the spec, 2025 frontier models cheated in about half of cases (ImpossibleBench). Telling a model not to cheat barely changed its rate (METR). Read-only tests and a sanctioned way to stop and report were the measures that worked.
- **Agents push as the creator's GitHub user.** Anything the creator can do in the repo, an agent session can do. No lock is tamper-proof; the aim is to make tampering hard and loud.

## Decision

### 1. Who does what
| Work | Tier |
|---|---|
| ADRs, interface stubs, acceptance tests, experiment pre-registrations, review of every change under `sim/` | strongest available model, high effort |
| Implementing one specified issue | mid-tier model (Sonnet class), medium or high effort |
| Search, summaries, mechanical edits | small model |

Per-model results are tracked: first-pass CI rate, defects found in review, protected-path attempts. Work moves up or down a tier on that evidence.

### 2. The issue is the spec
Every implementing issue follows [`docs/agents/task-template.md`](../agents/task-template.md): files and interfaces in scope, what is out of scope, an existing file to imitate, invariants touched, the failing acceptance tests by name, and one verification command.

### 3. Acceptance tests come first and are read-only
- The strong model writes acceptance tests under `sim/tests/acceptance/` and merges them, marked as expected failures for unbuilt features, before the implementing issue opens.
- Implementers remove the expected-failure mark when the feature passes. They may add tests elsewhere. They never edit, weaken, skip or delete an acceptance test.

### 4. Protected paths
`sim/tests/acceptance/`, `fixtures/golden/`, `.github/`, `.claude/`, accepted ADRs, `CLAUDE.md` and the lint, type-check and coverage settings. Three locks:

1. A `PreToolUse` hook in `.claude/settings.json` blocks edits to these paths in implementing sessions.
2. A required CI job fails any pull request whose diff touches them, unless the creator approves that pull request in a gated GitHub environment.
3. The reviewing model lists every protected-path change at the top of its review.

`.github/workflows/` stays the creator's alone. Agents are not given the Workflows permission; the creator pushes workflow changes.

### 5. A sanctioned way out
If a test seems to contradict the spec or an invariant, the agent stops, changes nothing in the test, and reports in the pull request. This instruction is in `CLAUDE.md` and in every issue.

### 6. Tests that special-casing cannot satisfy
- Property tests (Hypothesis) for every invariant.
- Small reference models in exact fractions, compared with the integer engine.
- Known-answer vectors for the draw function (ADR-0012).
- Nightly mutation testing on `sim/` once F3 lands.

### 7. Architecture as failing checks
- Import rules: `sim` imports nothing from `cognition`, `persistence` or `api`.
- Banned-API lint rules: `random`, `time`, `datetime.now`, numpy random in `sim/`.
- A prompt lexicon check (ADR-0019) once prompts exist.

### 8. Review
- Every pull request touching `sim/`, `rules/` or `schema/` gets a review by a stronger model than the one that wrote it, in a fresh context.
- The checklist is fixed: weakened assertions, new skips or expected failures, test-name special cases, new mocks around the code under test, edits outside the issue's scope, protected-path changes.
- Reviews are advisory. The required check `ci-ok` is what blocks a merge.

### 9. Sessions
One issue, one fresh session, one pull request under about 400 changed lines. `just test-fast` gives quiet, quick feedback.

## Alternatives considered
- **Instructions only.** Evidence says they barely change behaviour.
- **Hidden held-out tests.** They cut cheating but cost legitimate performance, and add little beyond a reviewing model.
- **Path-restricting push rules.** Not available on public repositories, hence the CI job.
- **A second GitHub identity for agents.** Would make code-owner approval binding. Worth doing if tampering is ever observed.

## Consequences
- The first backlog item (G1) builds these locks before feature work starts. The CI part needs the creator to push a workflow file.
- Writing acceptance tests first costs strong-model time up front and saves review time later.
- Revisit when a managed review service becomes available on the creator's plan.

## References
- ImpossibleBench (arXiv 2510.20270); METR, "Recent frontier models are reward hacking" (2025); EvilGenie (arXiv 2511.21654).
- Claude Code hooks guide and best-practices documentation.
