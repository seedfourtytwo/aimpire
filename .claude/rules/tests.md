---
paths:
  - "**/tests/**"
  - "**/test_*.py"
  - "**/*.test.ts"
  - "**/*.test.tsx"
  - "**/*.spec.ts"
  - "**/conftest.py"
---

# Test rules (loaded when touching tests)

- TDD: the test exists and has been **seen failing for the expected reason** before production code
  is written (AGENTS.md §3.1).
- One behaviour per test, named as a sentence. Test through public interfaces.
- Deterministic only: fixed seeds, frozen fixtures, injected clock, no network, no sleeps.
- Invariants (conservation, non-negative inventories, permutation invariance, no cross-civ leakage,
  replay hash equality) get hypothesis property tests.
- Never weaken, skip or delete a test to make code pass. If a test is wrong, say why and fix it in
  its own commit with the reason in the message.
- Keep test files under 300 lines; shared setup goes in fixtures/`conftest.py`.
