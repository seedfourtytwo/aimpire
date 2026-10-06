# Review checklist

For the model or person reviewing a pull request (ADR-0016). Review in a fresh session, with a stronger model than the one that wrote the change. Report gaps, not style preferences.

## First line of the review
List every protected path the diff touches: `sim/tests/acceptance/`, `fixtures/golden/`, `.github/`, `.claude/`, `docs/adr/`, `CLAUDE.md`, lint and type-check settings, and the repo gates (`tools/checks/`, `ruff.toml`, `.pre-commit-config.yaml`). If there are none, say so.

## Tests
- [ ] No acceptance test was edited, weakened, skipped or deleted.
- [ ] No new `skip`, `xfail` or loosened tolerance without a reason in the pull request.
- [ ] No code path checks for a test name, a fixture value or a call count.
- [ ] No new mock around the code under test.
- [ ] New behaviour has a test that fails without it.

## Invariants (CLAUDE.md)
- [ ] `sim/` does no I/O and imports nothing from `cognition`, `persistence`, `api` or `cli`.
- [ ] No `random`, `time`, `datetime.now` or numpy random in `sim/`. Draws go through `aimpire.sim.rng`.
- [ ] No float is stored or hashed. Rates use the helpers in `aimpire.sim.fixed`.
- [ ] Sequential systems use the per-tick order; no reliance on set or dict order.
- [ ] Model output changes state only through the validator.
- [ ] Observations hold nothing a civilization could not have perceived.
- [ ] No institution, role name or outcome is hardcoded (ADR-0019). Prompts stay neutral.

## Scope
- [ ] Every change is within the issue's "In scope" list.
- [ ] No new dependency without a version checked against its primary source.
- [ ] No network call in a default or test path. No credentials anywhere.

## Determinism
- [ ] Golden hashes unchanged, or the change is declared, labelled and justified.
- [ ] Any change to draws, order, rounding or hashing cites ADR-0012 and bumps the rules version.

## Finish
- [ ] `just check` output is in the pull request.
- [ ] `docs/agents/STATUS.md` is updated.
