# CI Quality Gates

## Purpose

Define the CI check matrix, advisory vs blocking status, and phased strictness expectations.

## CI Platform

- GitHub Actions only (`.github/workflows/ci.yml`).

## Check Matrix

| Check | Scope | Status |
|---|---|---|
| Frontend lint + typecheck | `frontend` | Blocking |
| Backend lint (ruff) | `backend` | Blocking |
| Backend unit tests | `backend/tests` | Blocking |
| Docs lane integrity | `docs` + `docs/agents` + `docs/operations` | Blocking |
| Python typing (pyright) | `backend` | Advisory |
| TypeScript no-any phase 1 | `frontend/src/services`, `frontend/src/hooks`, `frontend/src/types` | Advisory |

## Local Command Matrix

- Frontend lint: `npm run lint`
- Frontend typecheck: `npm run typecheck --workspace=frontend`
- Backend lint: `uv run ruff check backend`
- Backend tests: `uv run pytest backend/tests -q`
- Docs lane checks: `pwsh -File scripts/check-docs-governance.ps1`
- TS no-any phase 1: `npm run lint:ts-no-any:phase1`
- Python typing advisory: `npx pyright backend`

## Phased Strictness Backlog

1. Reduce pyright advisory noise and promote to blocking when stable.
2. Expand no-any domains from phase 1 to all frontend source.
3. Reconcile mypy role with pyright-canonical policy and document final split.

---

**Status**: Active  
**Last Updated**: 2026-02-22  
**Owner**: Engineering
