---
paths:
  - "**/tests/**"
  - "**/test_*.py"
  - "**/conftest.py"
  - "**/*.test.*"
  - "**/*.spec.*"
---

# Tests (loaded when touching any test)

- `sim/tests/acceptance/` is protected and read-only for implementers (ADR-0016). The only allowed
  change is removing an `xfail` mark once the feature passes — and only in a session allowed to.
- Your own tests go in `sim/tests/unit/` or `sim/tests/property/`, written **before** the code and
  seen failing for the right reason.
- One behaviour per test, named as a sentence; test through public interfaces; no mocks around the
  code under test; no checks on call counts or test names.
- Deterministic only: fixed seeds, frozen fixtures, injected clock, no network, no sleeps.
- Invariants get Hypothesis property tests.
- Never weaken, skip or delete a test to make code pass. If a test seems wrong, stop and report it.
- Keep test files under 300 lines; shared setup goes in fixtures/`conftest.py`.
