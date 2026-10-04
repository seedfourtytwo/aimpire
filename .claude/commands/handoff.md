---
description: End-of-session handoff (update STATUS.md, write handoff note)
---
Wrap up this session so the next agent can continue without this conversation:

1. Run `just check` and record the real result.
2. If work remains on this branch, copy `docs/agents/handoff-template.md` to `docs/agents/handoff-<slug>.md`, where `<slug>` is the branch name with `/` replaced by `-` (e.g. `agent/12-rng` → `handoff-agent-12-rng.md`), and fill it in.
3. Only in the PR's final commit: update your own lines in `docs/agents/STATUS.md` (In flight, items you closed, new blockers) and delete this branch's handoff note. Say what works, naming the tests that prove it, what doesn't, the exact next steps and how to resume.
4. Only describe tested behaviour as working.
