# Research notes

Background research behind the decisions. Notes are dated snapshots and are not updated after the decision they informed; the [ADRs](../adr/README.md) are binding. Each note's status says how far to trust it today.

| Note | Topic | Informed | Status |
|---|---|---|---|
| [00 Brief](00-brief.md) | Short version of the original specification | All early research | Historical: predates the name, the web client and the milestone order |
| [10 Client & rendering](10-client-rendering.md) | Web versus Godot, map rendering, UI | ADR-0002 | Background; client still deferred |
| [20 Backend & data](20-backend-data.md) | Python runtime, SQLite, replay | ADR-0003, ADR-0004 | Background; built |
| [30 Model layer](30-model-layer.md) | Provider adapters, structured output, costs | ADR-0005, ADR-0009 | Background; per-year cost figures are three times too high (ADR-0011) |
| [40 CI/CD & workflow](40-cicd-workflow.md) | GitHub Actions, agent workflow | ADR-0006, ADR-0016 | Background; uses old epic numbers E1–E15 |
| [50 Simulation design](50-simulation-design.md) | First-slice world rules | ADR-0007, ADR-0008 | Background; scope since reordered (ADR-0015) |
| [70 Social systems](70-social-systems.md) | Trade, belief, politics, conflict | ADR-0019 | Partly superseded: its institution menus were replaced by primitives (ADR-0019) |
| [80 Planning review](80-plan-review-2026-10-04.md) | Gaps, evidence, reordered build, research design, costs | ADRs 0011–0019 | **Read first.** Current reasoning for the plan |
| [90 Tinkering Lab & world physics](90-tinkering-lab-and-world-physics.md) | World constants, scaling laws, twin worlds | ADR-0020 | Current |
| [91 Native minds](91-native-minds.md) | Training small models on in-world text only | ADR-0021 | Current |
| [92 Predator-prey inspiration](92-predator-prey-inspiration.md) | Lessons from a neuroevolution video | Proposals for M2 and M4 | Current; proposals not yet accepted |
