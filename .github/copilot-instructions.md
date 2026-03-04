"Azure Architect Assistant" is a monorepo:
- Frontend: React 19 + TypeScript 5 + Vite + TailwindCSS 4.1
- Backend: Python 3.10+

 Agent Execution Contract (Global)
- Do exactly what was requested; avoid extra scope.
- Make smallest safe diff; no unrelated refactors.
- Do not run lint/tests/build unless explicitly requested.
- Do not apply unsolicited fixes outside requested scope.
- Never modify `.env`.
- Ask approval before major dependencies/frameworks/architecture shifts.

Tooling and Dependency Standards
- Python commands and dependency operations must use `uv`.
- Frontend dependencies must follow npm workspace + lockfile flow.

Development Method: TDD (Global, Mandatory)

For all non-trivial changes, follow Red → Green → Refactor:

1. *Red**: define/update a failing test for requested behavior.
2. **Green**: implement the smallest change to pass tests.
3. **Refactor**: improve structure without changing behavior.

TDD expectations:
- include happy path + edge case + error/invalid-input coverage when relevant;
- every bug fix includes a regression test;
- if tests are intentionally omitted, explicitly justify why in the task output.

Documentation Obligations
- Prefer updating documentation than create new ones; if new docs are needed, update `/docs/README.md` with links and summaries.
- ALWAYS update or create relevant docs for any change, even if not explicitly requested; documentation is part of the deliverable.
- Canonical docs are under `/docs`.
- Lane model is mandatory:
  - Agent lane: `/docs/agents`
  - Human lane: `/docs/<domain>`
- Always update relevant docs and keep `/docs/README.md` accurate.

