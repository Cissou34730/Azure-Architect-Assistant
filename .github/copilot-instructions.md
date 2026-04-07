"Azure Architect Assistant" is a monorepo:
- Frontend: React 19 + TypeScript 6 + Vite + TailwindCSS 4.1
- Backend: Python 3.10+

 Agent Execution Contract (Global)
- Do exactly what was requested; avoid extra scope.
- Make smallest safe diff; no unrelated refactors.
- Do not apply unsolicited fixes outside requested scope.
- All settings in the backend must be handle throug AppSettings abstaction, no direct import of any variable in other module.
- Never modify `.env`.
- Ask approval before major dependencies/frameworks/architecture shifts.
- When multiple files need to be changed in a chat session, create a branch. If a branch has already been created in the session, use the existing one.
- Run multiple incremental commits with clear messages to show progress and allow easy rollbacks if needed.

Tooling and Dependency Standards
- Python commands and dependency operations must use `uv`.
- Frontend dependencies must follow npm workspace + lockfile flow.

Development Method: TDD (Global, Mandatory)
Before adding or modifying code add the test first and validate it fails. Then implement the change and validate the test passes. Finally, refactor if necessary and validate tests still pass.

TDD expectations:
- include happy path + edge case + error/invalid-input coverage when relevant;
- every bug fix includes a regression test;
- if tests are intentionally omitted, explicitly justify why in the task output.

Documentation Obligations, all changes must be reflected in documentation:
- Prefer updating documentation than create new ones; if new docs are needed, update `/docs/README.md` with links and summaries.
- ALWAYS update or create relevant docs for any change, even if not explicitly requested; documentation is part of the deliverable.
- Canonical docs are under `/docs`.
- Lane model is mandatory:
  - Agent lane: `/docs/agents`
  - Human lane: `/docs/<domain>`
- Always update relevant docs and keep `/docs/README.md` accurate.

