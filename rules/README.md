# Rules data

Versioned, authored data that the simulation loads: calendar, rates, transformation rules. A hot path: each change goes in its own pull request and bumps the rules version (`docs/agents/workflow.md`).

- Rates are written with their period, `{ppm: N, per: year | season | tick}` (ADR-0011). Never as a per-tick permille constant.
- Nothing here names an institution, a role or a belief (ADR-0019).
