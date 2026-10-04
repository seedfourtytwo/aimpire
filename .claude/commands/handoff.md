---
description: End-of-session handoff (update STATUS.md, write handoff note)
---
Wrap up this session so the next agent can continue without this conversation:

1. Run `just check` and record the real result.
2. Update `docs/agents/STATUS.md`: phase, what's in flight, next up, blockers.
3. If work remains on this branch, copy `docs/agents/handoff-template.md` to `docs/agents/handoff-<branch>.md` and fill it in. Say what works, naming the tests that prove it, what doesn't, the exact next steps and how to resume.
4. Only describe tested behaviour as working.
