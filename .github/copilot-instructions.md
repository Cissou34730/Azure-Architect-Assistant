"Azure Architect Assistant" is a monorepo:
- Frontend: React 19 + TypeScript 5 + Vite + TailwindCSS 4.1
- Backend: Python 3.10+

## 1) Priority and Scope

1. User request in current chat (highest).
2. This file (`copilot-instructions.md`) for global behavior.
3. File-scoped instructions (`*-instruction.md`) when `applyTo` matches.

When rules conflict, follow the highest item above.

## 2) Agent Execution Contract (Global)

- Do exactly what was requested; avoid extra scope.
- Make smallest safe diff; no unrelated refactors.
- Do not run lint/tests/build unless explicitly requested.
- Do not apply unsolicited fixes outside requested scope.
- Never modify `.env`.
- Ask approval before major dependencies/frameworks/architecture shifts.

## 3) Delivery Quality Standards (Global)

- Validate and sanitize all external inputs.
- Use descriptive names; avoid hardcoded magic values when config exists.
- Keep behavior changes backward-compatible unless the request explicitly requires breaking change.
- Keep changes reviewable and tightly scoped.

## 4) Tooling and Dependency Standards

- Python commands and dependency operations must use `uv`.
- Frontend dependencies must follow npm workspace + lockfile flow.

## 5) Development Method: TDD (Global, Mandatory)

For all non-trivial changes, follow Red → Green → Refactor:

1. **Red**: define/update a failing test for requested behavior.
2. **Green**: implement the smallest change to pass tests.
3. **Refactor**: improve structure without changing behavior.

TDD expectations:
- include happy path + edge case + error/invalid-input coverage when relevant;
- every bug fix includes a regression test;
- if tests are intentionally omitted, explicitly justify why in the task output.

Execution constraint:
- do not run tests unless the user explicitly requests execution.

## 6) Documentation Obligations

- Canonical docs are under `/docs`.
- Lane model is mandatory:
  - Agent lane: `/docs/agents`
  - Human lane: `/docs/<domain>`
- For significant changes, update relevant docs and keep `/docs/README.md` accurate.

## 7) Escalation

- Request security/infra review for secrets, auth, IAM, network exposure, or infra-risking changes.
- Request explicit user approval before major dependency or architecture changes.
