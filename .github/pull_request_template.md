## Summary
<!-- What changed and why. Link the issue: Closes #… -->

## Impact
- **Determinism:** none / golden hashes changed (explain, `golden-update` label, rules version bumped)
- **Schema/contracts:** none / regenerated (client updated)
- **New dependencies:** none / list (versions verified against primary sources)
- **Network in default/test paths:** none
- **Not validated:** <!-- what you could not test, and why -->

## Definition of done (AGENTS.md §5.4)
- [ ] Tests written first and seen failing for the right reason; suite green
- [ ] `just check` passes locally (lint, format, types, shape limits, repo hygiene)
- [ ] Tests added (unit + property for invariant-bearing code)
- [ ] Provenance labels correct on new output paths
- [ ] Fresh-context review done (`/fresh-review`) for risky areas
- [ ] Docs / domain rules / ADR updated where relevant
- [ ] `docs/agents/STATUS.md` updated (and handoff note if work continues)

## Agent session
<!-- Optional: link to the Claude Code session -->
