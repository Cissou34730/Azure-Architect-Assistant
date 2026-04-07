# ADR: Parallel-Work Architecture Foundation

- Status: Accepted for Phase 0/1
- Date: 2026-04-01
- Related plan: [PARALLEL_WORK_ARCHITECTURE_IMPLEMENTATION.md](./PARALLEL_WORK_ARCHITECTURE_IMPLEMENTATION.md)

## Context

The monorepo has grown around horizontal folders on both the backend and frontend. That shape works for a single delivery thread, but it slows down parallel work and makes AI-assisted changes riskier because feature ownership is implicit instead of structural.

The current codebase also has two practical constraints:

1. `backend/app/agents_system` is a legitimate platform/orchestration layer and cannot be treated as just another feature package yet.
2. `ProjectState.state` is still a live JSON integration boundary for architecture inputs, agent artifacts, and some workspace metadata, so decomposition has to be staged and audited before any write-path removal.

## Decision

Adopt a lane-based, feature-first target architecture and implement it in phases.

Phase 0/1 establish the governance and enforcement foundation first:

1. Document the target structure and lane ownership.
2. Audit real `ProjectState` usage before planning table decomposition.
3. Freeze new top-level horizontal modules with warning-oriented CI checks.
4. Add initial import-boundary enforcement that preserves current behavior while making architectural drift visible.

Later phases will move code into feature-owned frontend and backend packages, introduce feature contracts, and replace direct `ProjectState` coupling with feature-owned stores and composed workspace views.

## Target Layout

### Backend target

```text
backend/app/
|- features/
|  |- projects/
|  |- agent/
|  |- checklists/
|  |- knowledge/
|  |- ingestion/
|  |- diagrams/
|  \- settings/
|- shared/
|  |- db/
|  |- config/
|  |- ai/
|  |- mcp/
|  \- logging/
|- agents_system/
|- main.py
|- lifecycle.py
\- service_registry.py
```

### Frontend target

```text
frontend/src/
|- features/
|  |- projects/
|  |- agent/
|  |- diagrams/
|  |- knowledge/
|  |- ingestion/
|  \- settings/
|- shared/
|  |- ui/
|  |- http/
|  |- config/
|  |- lib/
|  \- hooks/
\- app/
```

## Dependency Rules

The foundation phase adopts these rules:

1. Routers depend downward on services and models.
2. Selected router packages stay independent from each other.
3. `agents_system` is treated as a platform layer that must not depend on HTTP routers.
4. New top-level files under frozen horizontal directories are warning-only CI violations until the large folder moves are complete.
5. Frontend baseline rules forbid top-level shared modules from importing feature modules and warn when feature modules reach back into top-level services, hooks, or types.

## Alternatives Considered

### Keep the current horizontal structure

Rejected because it keeps ownership implicit, increases review surface area, and makes boundary enforcement largely social instead of automatic.

### Big-bang folder move

Rejected because it would combine architectural cleanup, data migration, and dependency rewiring into one high-risk change set with poor rollback characteristics.

### Dynamic frontend module registration

Rejected for now. Static manifests are easier to grep, review, and refactor, especially for AI coding agents.

## Consequences

Positive:

1. The repo now has explicit architecture documentation and CI hooks for the migration.
2. Phase 4 planning can rely on observed `ProjectState` data instead of assumptions.
3. The architecture baseline is enforceable without forcing the large feature moves immediately.

Trade-offs:

1. The initial import-linter configuration is intentionally weak because the final feature layout is not in place yet.
2. Frontend ESLint enforcement starts as a baseline that exposes coupling rather than fully prohibiting it.
3. `agents_system` and `ProjectState` remain special cases until the later carve-out and decomposition phases land.