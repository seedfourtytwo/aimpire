# ADR-0001: Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** creator

## Context
The project will be built over months, mostly by Claude Code agents working in separate cloud sessions. No single session remembers the reasoning of the previous one. Decisions need to survive in the repository.

## Decision
- Architecturally significant decisions are recorded as ADRs in `docs/adr/` using the template.
- Lower-stakes choices and assumptions go in `docs/plan/decision-log.md` (one line each, dated).
- Research that informs a decision goes in `docs/research/` and is linked from the ADR.
- Agents propose; the creator accepts.

## Consequences
- Every new session can rebuild context from `CLAUDE.md` → `docs/agents/STATUS.md` → relevant ADRs.
- Slight overhead per decision; mitigated by the `/adr` command in `.claude/commands/`.
