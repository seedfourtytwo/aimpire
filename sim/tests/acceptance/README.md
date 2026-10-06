# Acceptance tests

Protected (ADR-0016). Read this before touching anything here.

- These tests are written **before** the code, by the planning model, from the backlog item and its ADRs.
- They are **read-only for implementing sessions**. Do not edit, weaken, skip, rename or delete them. A hook and a CI check enforce this.
- A test for a feature that does not exist yet is marked `@pytest.mark.xfail(strict=True, reason="<backlog id>")`. When a change makes it pass, the mark is removed — and nothing else changed — by the S-tier orchestrator in an `AIMPIRE_ALLOW_PROTECTED=1` session, or by the creator; an implementer lists the tests in its pull request instead (ADR-0022 amends ADR-0016 §3). Strict mode makes an unexpected pass fail the run, so the mark cannot be forgotten.
- Every test here also carries `@pytest.mark.acceptance` (or a module-level `pytestmark`).
- **If a test seems to contradict the issue or an ADR, stop.** Explain it in the pull request and wait. Do not change the test to fit the code.

Put your own additional tests in `tests/unit/` or `tests/property/`.
