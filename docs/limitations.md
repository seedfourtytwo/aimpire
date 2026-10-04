# Known limitations

An honest, running list (AGENTS.md §4.3). Code marks these with `# SIMPLIFICATION:` or
`# KNOWLEDGE-LEAK:` and links here. Remove an entry only when the limitation is actually gone.

| Area | Limitation | Since | Mitigation / plan |
|---|---|---|---|
| Cognition | Pretrained models already know real-world technology; prompts cannot erase it. Civilizations may *propose* advanced ideas. | spec §5 | The sim only executes authored processes with evidence; optional abstract material names (ADR-0008). Disclosed in results. |
| Cognition | One controller per civilization approximates collective decision-making; it does not model individual minds. | ADR-0008 | Declared in UI and exports; faction minds are a named extension point. |
| Replay | Fresh reruns with live models are not reproducible; only recorded replay is hash-identical. | ADR-0004 | Labelled `LIVE` vs `RECORDED`; never compared by hash. |
| Agent tooling | Claude Code hooks are guardrails, not security boundaries; an agent could route around them via other tools. | ADR-0010 | CI (`ci-ok`) and fresh-context review remain the gates. |
| Agent tooling | `guard_bash.py` is a best-effort parser: exotic shell (functions, aliases, `xargs` argument building, scripts written to disk then run) can still evade it. Implicit pushes are checked against the current branch only when git is available. | ADR-0010 | Agents never work on `main` (AGENTS.md §5.2); the `main` ruleset (Q6) blocks pushes server-side; CI and review gate everything. |
| Agent tooling | No local secret scan before push yet. | ADR-0010 | Planned: gitleaks in `security.yml` (ADR-0006) and GitHub push protection (Q6). |
| Agent tooling | Nesting depth (≤ 4) is not yet machine-checked for Python (ruff rule is preview-only). | ADR-0010 | Checked in review; enable when the rule is stable. |
