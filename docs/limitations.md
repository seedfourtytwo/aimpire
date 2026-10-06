# Known limitations of the agent tooling

An honest list of what the agent guard rails do not do (ADR-0016, ADR-0022). Remove an entry only
when the limitation is actually gone. Simulation and research limitations belong with their
milestone docs and experiment reports.

| Limitation | Mitigation |
|---|---|
| Claude Code hooks are guardrails, not security boundaries. Agents push as the creator's GitHub user, and a determined agent can route around a hook (for example by writing a script and running it). | CI (`ci-ok`), the planned protected-path CI job (backlog G1a) and fresh-context review are the real gates. |
| `guard_bash.py` is a best-effort shell parser. Functions, aliases, `xargs`-built commands and scripts written to disk can evade it. An implicit push is checked against the current branch only when git is available. | Agents never work on `main`; the `main` ruleset blocks direct pushes server-side. |
| An `implementer` cannot remove an acceptance test's `xfail` mark itself, because the file is protected. | The orchestrator removes it in an `AIMPIRE_ALLOW_PROTECTED=1` session, or the PR lists the marks for the creator. |
| The repo-wide gates run in CI only inside `check-sim`, so a pull request that touches only `tools/` or `.claude/` skips them in CI. | Local `just check` and the prek pre-commit hook run them; a dedicated `repo` job (backlog G1e) is for the creator to add. |
| There is no local secret scan before a push. | GitHub secret scanning and push protection (workflow.md, recommended repo settings). |
| Nesting depth is not machine-checked for Python (the ruff rule is preview-only). | Checked in review. |
