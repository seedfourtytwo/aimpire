---
description: Tufte and accessibility audit of client changes
argument-hint: [view or component, optional]
---
Delegate to the `ui-auditor` subagent: audit $ARGUMENTS (default: every view changed on this branch
under `client/web/`) against the checklist in `docs/agents/ui-rules.md`, using Playwright
screenshots in light and dark mode at desktop and 390 px widths.

Relay its findings (Blocking / Should fix / Nit) with screenshot references. Say plainly if
screenshots could not be rendered.
