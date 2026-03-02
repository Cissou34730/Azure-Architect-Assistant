# Source of Truth Matrix

## Purpose

Define authoritative policy sources, precedence, ownership, and enforcement mechanisms.

## Precedence Chain

When rules conflict, apply this order:

1. Direct user request in the active task.
2. Repository governance docs under `/docs/operations`.
3. Agent runtime instructions under `/.github/copilot-instructions.md`.
4. Language- and domain-specific instructions under `/.github/*-instruction.md`.
5. Tooling configuration (`eslint.config.js`, `tsconfig.json`, `pyproject.toml`, `mypy.ini`, `pyrightconfig.json`).

## Policy Ownership and Enforcement

| Policy Area | Canonical Source | Owner | Enforcement Mechanism |
|---|---|---|---|
| Documentation lane model and update obligations | `/docs/operations/DOCUMENTATION_GOVERNANCE.md` | Engineering | Documentation review + docs index checks |
| Process workflow and traceability | `/docs/operations/WORKFLOW_TRACEABILITY_RUNBOOK.md` | Engineering | Issue templates + PR/commit review |
| Agent operating rules | `/.github/copilot-instructions.md` | Engineering | Agent runtime behavior |
| TypeScript coding conventions | `/.github/copilot-typescript-instruction.md` | Frontend | ESLint + TypeScript typecheck |
| Python coding conventions | `/.github/python-instruction.md` | Backend | Ruff + pytest + typing checks |
| Terraform/Azure conventions | `/.github/terraform-instruction.md` | Platform | IaC review workflow |
| Frontend lint/type authority | `/eslint.config.js`, `/frontend/tsconfig.json` | Frontend | CI lint/type jobs |
| Python lint/type authority | `/pyproject.toml`, `/mypy.ini`, `/pyrightconfig.json` | Backend | CI lint/type jobs |

## Active Contradictions and Resolutions

### Python Typing Authority

- Plan target: Pyright canonical authority.
- Current state: `pyrightconfig.json` disables analysis while `mypy.ini` is strict and `pyproject.toml` contains permissive mypy settings.
- Resolution path:
  1. Align one canonical Python type checker profile.
  2. Convert non-canonical checker to scoped support role.
  3. Reflect final policy in runbook and CI matrix.

### Backend Python Execution Path

- Policy target: mandatory `uv` backend execution.
- Current state: task/scripts still call `.venv\Scripts\python.exe` directly.
- Resolution path:
  1. Standardize commands to `uv run` / `uv python` in scripts/tasks/docs.
  2. Keep one compatibility path only where tooling requires direct interpreter.

## Approval Notes

- This matrix is the governance baseline for future CI gate hardening.
- Policy conflicts must be logged here before enforcement changes land.

---

**Status**: Active  
**Last Updated**: 2026-02-22  
**Owner**: Engineering