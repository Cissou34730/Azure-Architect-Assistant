# Feature Development Guide

## Purpose

Practical rules for adding or extending a feature in the parallel-work architecture without reintroducing the old horizontal sprawl.

## Backend pattern

Create or extend a feature under `backend/app/features/<feature>/`.

- `api/` owns FastAPI routers and response/request models.
- `application/` owns orchestration and use-case logic.
- `domain/` owns domain rules and pure business logic.
- `infrastructure/` owns repositories, persistence adapters, and feature-local integration code.
- `contracts/` owns data exchanged across feature boundaries.

Use `backend/app/shared/` for runtime concerns that are genuinely cross-cutting: config, DB sessions, AI clients, MCP helpers, logging.

Do not introduce new top-level modules under `backend/app/services/` or `backend/app/routers/`.

## Frontend pattern

Create or extend a feature under `frontend/src/features/<feature>/`.

- `api/` owns HTTP clients.
- `components/` owns feature UI.
- `hooks/` owns feature-local state/orchestration hooks.
- `types/` owns feature-local TypeScript contracts.
- `workspace.manifest.ts` owns route metadata and, where relevant, workspace registration details.

Use `frontend/src/shared/` only for reusable UI, hooks, HTTP helpers, config, and utilities that are not feature-specific.

Do not reintroduce root `frontend/src/{hooks,services,types}` shims.

## Adding a workspace tab

Projects workspace tabs are feature-owned and registry-driven.

1. Add or update the tab definition in `frontend/src/features/projects/workspace.manifest.ts`.
2. Add the tab renderer in `frontend/src/features/projects/workspaceTabRegistry.tsx`.
3. Keep dynamic document-tab handling in `WorkspaceTabContent.tsx`; static feature-owned tabs belong in the registry.
4. If the tab consumes project state, use the canonical `ProjectState` payload sourced from `/api/projects/{projectId}/workspace`.

## Defining a cross-feature contract

Create the contract in `backend/app/features/<feature>/contracts/`.

- Use small, explicit dataclasses or Pydantic models.
- Export only what another feature or the platform layer actually needs.
- Prefer a contract over importing another feature's internals.
- Keep `agents_system` dependent on contracts, not feature internals, whenever feature extraction is practical.

## Registering an agent tool

The registration/factory layer remains in `backend/app/agents_system/tools/`.

1. Put feature-owned tool logic with the owning feature when possible.
2. Keep `agents_system/tools/` focused on registration and assembly.
3. Ensure emitted state updates still flow through the canonical state update parser and decomposition-aware write paths.
4. Update feature contracts or docs if the tool changes cross-feature data ownership.

## Verification checklist

- Backend imports still satisfy `.importlinter`.
- Frontend imports still satisfy the architecture ESLint rules.
- New project-state reads use `/api/projects/{projectId}/workspace` unless maintaining explicit legacy compatibility.
- Docs are updated in both the human lane and the agent lane when architecture ownership changes.