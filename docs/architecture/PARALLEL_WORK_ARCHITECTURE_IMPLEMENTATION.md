# Monorepo Parallel-Work Architecture — Detailed Implementation Plan

> **Status**: Draft — Pending review  
> **Parent plan**: [Monorepo Parallel-Work Architecture Plan](#summary)  
> **Audience**: Human + AI coding agents  
> **Last updated**: 2026-04-02

---

## Plan Review & Challenges

Before implementing, the following concerns must be resolved or acknowledged.

### C1 — Team lanes assume a team size that may not exist yet

The plan defines 5 lanes mapped to 4 teams + 1 platform lane. The current repo appears operated by one developer plus AI coding agents. **Risk**: CODEOWNERS and formal cross-team contracts add process overhead without yielding the parallel-work benefit if there aren't actually parallel workers yet.

**Resolution**: Keep the lane model as a logical boundary for AI agents (each subagent works in one lane), but defer CODEOWNERS enforcement until actual team growth. Use CI boundary checks only — they benefit solo developers and agents alike.

### C2 — ProjectState decomposition is partially done already

The plan states "conversations and trace data stay on their existing tables" as a migration step. But `messages`, `project_threads`, `project_trace_events`, `checklists`, and `checklist_item_evaluations` are **already on dedicated tables** in the projects DB. The `state` JSON blob only holds architecture inputs (`context`, `nfrs`, `applicationStructure`, `dataCompliance`, `technicalConstraints`, `openQuestions`).

**Resolution**: The plan's Phase 4 should focus on what's actually in the JSON blob today: architecture inputs and possibly candidate architectures/ADRs/findings that the agent tools write via `state_edit_service.py`. Verify exactly which artifact families still write to the JSON blob vs. which already have dedicated tables.

### C3 — Agent system is cross-cutting and not addressed

`agents_system/` is the most complex module (agents, tools, LangGraph orchestration, memory, checklists). It legitimately accesses project state, diagrams, KB, and ingestion. The plan's feature model doesn't explain where agents_system lives or how `import-linter` rules accommodate it.

**Resolution**: Treat `agents_system` as a **platform orchestration layer** (in the `platform/shared` lane), not as a feature. It imports from feature contracts. Feature tools (e.g., `aaa_artifacts_tool.py`, `kb_tool.py`) move into their respective features and are registered via the tool factory.

### C4 — Frontend carve-out before backend means temporary API misalignment

Phase 2 (frontend carve-out) happens before Phase 3 (backend carve-out + WorkspaceView). Frontend feature modules will initially call the same monolithic endpoints (`/api/projects/{id}/state`). This is fine, but should be explicitly called out as intentional.

**Resolution**: Frontend features initially wrap existing shared services. The service files move physically into features, but the API calls don't change until Phase 3 delivers the new endpoints.

### C5 — WorkspaceModule dynamic registration vs explicit imports

The plan proposes plugin-like `WorkspaceModule` registration for UI composition. For an AI-agent-optimized codebase, explicit imports are more discoverable than dynamic registration. Agents can trace static imports; magic registration patterns require convention knowledge.

**Resolution**: Use a **static manifest** pattern instead of dynamic registration. Each feature exports a `workspace.manifest.ts` with `WorkspaceModule` metadata. The workspace shell imports all manifests explicitly. This is refactor-friendly and grep-friendly.

### C6 — Data migration scripts are missing from the plan

Moving artifact families from JSON blob to tables is a **data migration**, not just a code change. Each artifact family needs an Alembic migration script to create the new table and a backfill script to move existing data.

**Resolution**: Each Phase 4 sub-task must include: (1) Alembic migration for new table, (2) backfill script, (3) dual-read adapter, (4) write-path switch, (5) verification, (6) old write-path removal.

### C7 — import-linter configuration for agents_system

`import-linter` rules must accommodate the agents_system's legitimate cross-feature access. Without an exemption strategy, the first CI run will have hundreds of violations.

**Resolution**: Define agents_system as a "platform" package with explicit allowed imports via `import-linter` contract types. Use `independence` contracts for features and `layers` contracts for the platform-to-feature direction.

---

## Detailed Phase Breakdown

### Phase 0 — Governance Foundation

**Goal**: Establish architectural boundaries in documentation and tooling before any code moves.

#### Task 0.1 — Write the Architecture Decision Record (ADR)
- [x] Create `docs/architecture/ADR-parallel-work-architecture.md`
- [x] Document: decision, context, considered alternatives, chosen approach, consequences
- [x] Include the target folder layout for backend and frontend
- [x] Include the dependency rules and contract patterns
- [x] Reference this implementation plan

> **Delegation**: Subagent `speckit.specify` or `speckit.plan` — provide the plan summary as input and ask for an ADR in the project's ADR format.

#### Task 0.2 — Freeze new horizontal modules
- [x] Add a lint rule or CI check that fails if new files are created directly under:
  - `backend/app/services/` (top-level, not inside a feature)
  - `backend/app/routers/` (top-level, not inside a feature)
  - `frontend/src/hooks/` (top-level)
  - `frontend/src/services/` (top-level)
  - `frontend/src/types/` (top-level)
  - `frontend/src/components/` (top-level, outside `common/`)
- [x] Document the freeze policy in the ADR
- [x] Add to CI as a warning initially (not blocking)

> **Delegation**: Subagent `Explore` — find all existing CI configuration (GitHub Actions workflows, pre-commit hooks) to understand where to add the check. Then implement with a simple shell script or Python check in CI.

#### Task 0.3 — Document lane ownership
- [x] Create `docs/architecture/LANE_OWNERSHIP.md`
- [x] Map each lane to its feature folders (backend + frontend)
- [x] List which existing modules belong to which lane
- [x] Defer CODEOWNERS file creation until team grows (per Challenge C1)

> **Delegation**: Manual or direct edit — this is a documentation-only task.

#### Task 0.4 — Audit what's actually in ProjectState JSON blob
- [x] Write a script that reads all `project_states` rows and catalogs which top-level keys exist in the JSON blobs
- [x] Determine which artifact families are stored in the blob vs. in dedicated tables
- [x] Produce a migration inventory: what needs to move, what's already separate
- [x] Document findings in `docs/architecture/PROJECTSTATE_DECOMPOSITION_INVENTORY.md`

> **Delegation**: Subagent (execution) — write and run a Python script against the SQLite DB.

---

### Phase 1 — Architecture Enforcement in CI

**Goal**: Add automated boundary checks so new code respects the target structure, even before moves happen.

#### Task 1.1 — Backend: install and configure import-linter
- [x] Add `import-linter` to dev dependencies via `uv add --dev import-linter`
- [x] Create `.importlinter` configuration file with initial contracts:
  - **Independence contract**: features cannot import each other's internals
  - **Layers contract**: `app.routers` → `app.services` → `app.models` (no reverse)
  - **Forbidden contract**: `app.services` must not import from `app.routers`
  - **Allowed exemptions**: `app.agents_system` can import from feature contracts (per C3/C7)
- [x] Write tests: `backend/tests/architecture/test_import_boundaries.py`
  - [x] Test: feature A cannot import feature B internals
  - [x] Test: shared cannot import from features
  - [x] Test: application layer cannot import router DTOs
- [x] Add to CI pipeline
- [x] **TDD**: Write the tests first, verify they detect a planted violation, then configure rules

Current Phase 1 baseline now includes planted-violation import-linter tests plus live contracts for `app.shared` and `app.features.projects.application`. Stronger feature-level contracts beyond the projects application boundary still move to Phase 3.12.

2026-04-07 follow-up: `app.shared.db` no longer re-exports an ingestion session helper. Ingestion DB access stays feature-owned so the `shared-foundation` import-linter contract remains enforceable by the architecture workflow.

2026-04-07 follow-up: `AgentsSettingsMixin` now resolves its default MCP config path from `backend/config/mcp/mcp_config.json`, matching the documented backend layout and unblocking startup without requiring an override.

> **Delegation**: Subagent (execution) — install dependency, create config, run initial lint pass, fix config until clean.

#### Task 1.2 — Frontend: configure ESLint no-restricted-imports
- [x] Add ESLint rules to `eslint.config.js`:
  - `no-restricted-imports` patterns:
    - `features/*/` cannot import from `features/*/` (cross-feature ban)
    - `features/*/` cannot import from top-level `hooks/`, `services/`, `types/` (once moved)
    - `shared/` cannot import from `features/`
- [x] Write architecture test: `frontend/src/architecture/import-boundaries.test.ts`
  - [ ] Test: planted cross-feature import is flagged
  - [x] Test: feature importing top-level services is surfaced
  - [x] Test: top-level shared modules importing features are flagged
- [x] Add to CI pipeline (warning mode initially, blocking after Phase 2)
- [ ] **TDD**: Write the test first, verify ESLint catches the planted violation

Frontend Phase 1 is a baseline, not the final boundary model. The current rules block top-level shared-to-feature imports and warn on feature-to-top-level coupling. Strict cross-feature bans remain deferred until Phase 2 produces stable feature-local import paths.

> **Delegation**: Subagent (execution) — update ESLint config, run lint, verify rules fire correctly.

#### Task 1.3 — Add CI workflow for architecture checks
- [x] Create or update `.github/workflows/architecture.yml`
- [x] Steps: install deps → run import-linter → run ESLint architecture rules
- [x] Initially non-blocking (`continue-on-error`) to avoid breaking current PRs
- [x] Promote to blocking after Phase 2 completion

> **Delegation**: Subagent (execution) — create workflow file, test locally with `act` or dry-run.

---

### Phase 2 — Frontend Carve-Out

**Goal**: Move UI code into feature modules so each capability owns its components, hooks, types, and API clients.

#### Implementation Note — 2026-04-01

- Canonical ownership now lives under `frontend/src/shared/*` and `frontend/src/features/{agent,diagrams,knowledge,ingestion,settings,projects}` for the moved Phase 2 surfaces.
- Route-backed feature manifests were added for `projects`, `knowledge`, and `ingestion`, plus manifest stubs for `agent`, `diagrams`, and `settings`.
- `frontend/src/app/routes.tsx` now sources the top-level workspace route modules from the static manifest registry instead of hardcoding every feature import.
- The top navigation now sources its route links from the same registry, while provider/model controls were split into a settings-owned component.
- `frontend/src/features/projects/workspace.manifest.ts` now also owns the unified project workspace shell sections, static tab catalog, left-panel tree entries, default tab, and route-intent aliases consumed by `UnifiedProjectWorkspace`, `workspaceHooks.ts`, and the left-panel sections.
- `frontend/src/features/projects/workspaceTabRegistry.tsx` now owns the static project tab-content registry keyed by manifest tab ids, so `WorkspaceTabContent.tsx` only handles dynamic document tabs directly.
- The temporary root compatibility layer has now been removed from `frontend/src/{hooks,services,types}` after normalizing the remaining agent, ingestion, knowledge, and settings imports onto feature-local modules.
- The now-obsolete root shim files, including `frontend/src/types/api.ts`, `frontend/src/services/proposalService.ts`, and `frontend/src/types/api-diagrams.ts`, were deleted once they had no live importers.

#### Preparation: Define target frontend layout

```
frontend/src/
├── features/
│   ├── projects/            (exists, expand)
│   │   ├── api/             projectService.ts, stateService.ts
│   │   ├── components/      (existing project components)
│   │   ├── hooks/           useProjectsData, useProjectSelector
│   │   ├── pages/           (existing)
│   │   ├── types/           api-project.ts
│   │   ├── context/         (existing)
│   │   └── workspace.manifest.ts
│   ├── agent/
│   │   ├── api/             agentService.ts, chatService.ts
│   │   ├── components/      AgentChatWorkspace, AgentChatPanel, ProjectState/*
│   │   ├── hooks/           (agent-specific hooks from components/agent/hooks/)
│   │   ├── types/           agent.ts, api-artifacts.ts
│   │   └── workspace.manifest.ts
│   ├── diagrams/
│   │   ├── api/             (diagram API calls, currently in agentService or inline)
│   │   ├── components/      MermaidRenderer, config/, diagram hooks
│   │   ├── hooks/           (diagram-specific hooks)
│   │   ├── types/           api-diagrams.ts
│   │   └── workspace.manifest.ts
│   ├── knowledge/
│   │   ├── api/             kbService.ts
│   │   ├── components/      KBWorkspace, KBQueryForm, KBQueryResults, KBSelector
│   │   ├── hooks/           useKBList, useKBQuery, useKBWorkspace
│   │   ├── types/           api-kb.ts
│   │   └── workspace.manifest.ts
│   ├── ingestion/
│   │   ├── api/             ingestionApi.ts
│   │   ├── components/      IngestionWorkspace, CreateKBWizard, wizard/*, etc.
│   │   ├── hooks/           useIngestionJob
│   │   ├── types/           ingestion.ts
│   │   └── workspace.manifest.ts
│   └── settings/
│       ├── api/             settingsService.ts
│       ├── components/      (settings UI)
│       ├── hooks/           useModelSelector
│       └── workspace.manifest.ts
├── shared/
│   ├── ui/                  Badge, Button, Card, LoadingSpinner, Toast, Navigation, etc.
│   ├── http/                (HTTP client, error handling)
│   ├── config/              (existing config/)
│   ├── lib/                 (existing utils/)
│   └── hooks/               useDebounce, useClickOutside, useFocusTrap, useErrorHandler
└── app/                     (shell, routing, layout)
```

#### Task 2.1 — Create shared/ scaffold and move UI primitives
- [x] Create `frontend/src/shared/ui/` directory
- [x] Move all `frontend/src/components/common/*` → `frontend/src/shared/ui/`
- [x] Create `frontend/src/shared/http/` — extract HTTP client logic from services
- [x] Move `frontend/src/utils/` → `frontend/src/shared/lib/`
- [x] Move `frontend/src/config/` → `frontend/src/shared/config/`
- [x] Move generic hooks (`useDebounce`, `useClickOutside`, `useFocusTrap`, `useErrorHandler`) → `frontend/src/shared/hooks/`
- [x] Update all imports across the codebase
- [x] Run TypeScript compilation: zero errors
- [x] Run existing tests: all pass

> **Delegation**: Subagent `ts-react-tw-refactor` — provide the file list and target paths. Ask it to move files, update imports, and verify compilation.

#### Task 2.2 — Carve out `features/agent/`
- [x] Create directory structure: `features/agent/{api,components,hooks,types}`
- [x] Move `components/agent/*` → `features/agent/components/`
- [x] Move `services/agentService.ts` → `features/agent/api/agentService.ts`
- [x] Move `services/chatService.ts` → `features/agent/api/chatService.ts`
- [x] Move `services/proposalService.ts` → `features/agent/api/proposalService.ts`
- [x] Move `types/agent.ts` → `features/agent/types/agent.ts`
- [x] Move `types/api-artifacts.ts` → `features/agent/types/api-artifacts.ts`
- [x] Move agent-specific hooks from `hooks/` → `features/agent/hooks/`
- [x] Create `features/agent/workspace.manifest.ts` with `WorkspaceModule` export
- [x] Update all imports
- [x] Run TypeScript compilation: zero errors
- [x] Run existing tests: all pass

> **Delegation**: Subagent `ts-react-tw-refactor` — same approach as 2.1.

#### Task 2.3 — Carve out `features/diagrams/`
- [x] Create directory structure: `features/diagrams/{api,components,hooks,types}`
- [x] Move `components/diagrams/*` → `features/diagrams/components/`
- [x] Move `types/api-diagrams.ts` → `features/diagrams/types/api-diagrams.ts`
- [x] Extract diagram API calls into `features/diagrams/api/diagramService.ts`
- [x] Move diagram hooks → `features/diagrams/hooks/`
- [x] Create `features/diagrams/workspace.manifest.ts`
- [x] Update all imports
- [x] Verify: TypeScript clean, tests pass

> **Delegation**: Subagent `ts-react-tw-refactor`.

#### Task 2.4 — Carve out `features/knowledge/`
- [x] Create directory structure: `features/knowledge/{api,components,hooks,types}`
- [x] Move `components/kb/*` → `features/knowledge/components/`
- [x] Move `services/kbService.ts` → `features/knowledge/api/kbService.ts`
- [x] Move `types/api-kb.ts` → `features/knowledge/types/api-kb.ts`
- [x] Move `hooks/useKBList.ts`, `hooks/useKBQuery.ts`, `hooks/useKBWorkspace.ts` → `features/knowledge/hooks/`
- [x] Create `features/knowledge/workspace.manifest.ts`
- [x] Update all imports
- [x] Verify: TypeScript clean, tests pass

> **Delegation**: Subagent `ts-react-tw-refactor`.

#### Task 2.5 — Carve out `features/ingestion/`
- [x] Create directory structure: `features/ingestion/{api,components,hooks,types}`
- [x] Move `components/ingestion/*` → `features/ingestion/components/`
- [x] Move `services/ingestionApi.ts` → `features/ingestion/api/ingestionApi.ts`
- [x] Move `types/ingestion.ts` → `features/ingestion/types/ingestion.ts`
- [x] Move `hooks/useIngestionJob.ts` → `features/ingestion/hooks/`
- [x] Create `features/ingestion/workspace.manifest.ts`
- [x] Update all imports
- [x] Verify: TypeScript clean, tests pass

> **Delegation**: Subagent `ts-react-tw-refactor`.

#### Task 2.6 — Carve out `features/settings/`
- [x] Create directory structure: `features/settings/{api,components,hooks}`
- [x] Move `services/settingsService.ts` → `features/settings/api/settingsService.ts`
- [x] Move `hooks/useModelSelector.ts` → `features/settings/hooks/`
- [x] Move settings-related UI (if any) into `features/settings/components/`
- [x] Update all imports
- [x] Verify: TypeScript clean, tests pass

> **Delegation**: Subagent `ts-react-tw-refactor`.

#### Task 2.7 — Expand existing `features/projects/`
- [x] Move `services/projectService.ts` → `features/projects/api/projectService.ts`
- [x] Move `services/stateService.ts` → `features/projects/api/stateService.ts`
- [x] Move `services/checklistService.ts` → `features/projects/api/checklistService.ts` (or to agent feature if checklists are agent-owned)
- [x] Move `types/api-project.ts` → `features/projects/types/api-project.ts`
- [x] Move `hooks/useProjectsData.ts` → `features/projects/hooks/`
- [x] Update all imports
- [x] Verify: TypeScript clean, tests pass

> **Delegation**: Subagent `ts-react-tw-refactor`.

#### Task 2.8 — Refactor workspace shell to manifest-based composition
- [x] Define `WorkspaceModule` TypeScript interface in `shared/lib/workspace-module.ts`:
  ```typescript
  export interface WorkspaceModule {
    id: string;
    zone: 'left-panel' | 'center-tabs' | 'right-panel';
    title: string;
    routeKey: string;
    load: () => Promise<React.ComponentType>;
    isVisible: (ctx: WorkspaceContext) => boolean;
  }
  ```
- [x] Create manifest files in each feature (per tasks above)
- [x] Create `app/workspace-registry.ts` that statically imports all manifests
- [x] Refactor the unified workspace component to render from the registry instead of hardcoded panels
- [x] Verify: all existing panels still render, routes still work
- [ ] Run E2E or manual smoke test of workspace navigation

> **Delegation**: Subagent `ts-react-tw-refactor` for the refactor. Manual or `webapp-testing` skill for verification.

#### Task 2.9 — Replace mega-provider with feature-scoped providers/hooks
- [x] Identify the current "wide project context" provider(s) in `contexts/` and `features/projects/context/`
- [x] Extract agent-specific state into `features/agent/` context or hooks
- [x] Extract diagram-specific state into `features/diagrams/` hooks
- [x] Extract KB-specific state into `features/knowledge/` hooks
- [x] Keep project-level state (project metadata, selection) in `features/projects/context/`
- [x] Verify: no feature imports from another feature's context
- [x] Run all tests

> **Delegation**: Subagent `ts-react-tw-refactor` — requires careful dependency analysis first. Use `Explore` subagent to map which components consume which context values.

#### Task 2.10 — Cleanup: remove empty old directories
- [ ] Verify `frontend/src/components/` only contains `common/` (now empty or redirected to `shared/ui/`)
- [x] Verify `frontend/src/hooks/` is empty or contains only re-exports
- [x] Verify `frontend/src/services/` is empty or contains only re-exports
- [x] Verify `frontend/src/types/` is empty or contains only re-exports
- [ ] Add re-export files in old locations if any external tools reference them (temporary)
- [x] Promote ESLint architecture rules to blocking in CI

> **Delegation**: Direct edit — small cleanup task.

---

### Phase 3 — Backend Carve-Out

**Goal**: Restructure backend into feature packages with clear boundaries, introduce `ProjectWorkspaceView`.

**Current branch status (2026-04-02)**

- Implemented an initial `backend/app/features/` scaffold for `projects`, `agent`, `checklists`, `knowledge`, `ingestion`, `diagrams`, and `settings`, plus `backend/app/shared/` for `config`, `db`, `ai`, `mcp`, `logging`, and `container`.
- Moved the **projects** HTTP surface into `features/projects/api/`, then removed the now-unused `routers/project_management/` compatibility package after repointing the top-level router facade directly at `app.features.projects.api`.
- Added initial cross-feature contracts for conversation, checklist, knowledge-base, diagram, runtime-selection, and `ProjectWorkspaceView` composition.
- Added `features/projects/application/workspace_composer.py`, `features/projects/infrastructure/workspace_repository.py`, and `GET /api/projects/{project_id}/workspace`.
- Moved the canonical projects application services for `project_service`, `document_service`, `state_edit_service`, `project_analysis_service`, `proposal_stream_service`, and `chat_service` into `backend/app/features/projects/application/`, while keeping `backend/app/services/project/` as thin compatibility re-export shims.
- Repointed the in-repo projects API layer (`_deps.py`, `project_router.py`, `document_router.py`, `state_router.py`) to import those canonical application modules directly.
- Kept `agents_system/` as the orchestration/platform layer. No tool registration was moved in this slice.
- Removed dead shared shim files (`app.core.app_logging`, `app.core.container`, `app.core.db`, and `app.projects_database`) plus empty placeholder directories under `agents_system/langgraph/runtime` and `features/ingestion/contracts`.
- Tightened backend import-linter with safe post-carve-out rules (`app.shared` must not import `app.features`; `app.features.projects.application` must not depend on `api` or other feature internals; `app.features.projects.api` must not fall back to `app.core`).
- Deferred the broad service/model relocations and `GET /state` composer unification to later cleanup. In-repo backend callers now resolve directly through `app.shared.config.app_settings`; `app.core.app_settings` remains only as an out-of-tree compatibility import target.

#### Implementation Note — 2026-04-02

- The application-layer move is intentionally compatibility-preserving: the legacy `app.services.project.*` modules remain importable and re-export the canonical implementations from `app.features.projects.application.*`.
- `chat_service.py` now lives canonically under the `projects` feature for this slice because that avoided widening the change into the agent feature. Long-term ownership between `projects` and `agent` remains an explicit follow-up decision.
- `project_service.py` no longer imports request DTOs from `features/projects/api/`; it now uses local structural typing so the projects application package stays independent of router DTOs.

#### Preparation: Define target backend layout

```
backend/app/
├── features/
│   ├── projects/
│   │   ├── api/              project_router.py, state_router.py, document_router.py, models.py
│   │   ├── application/      project_service.py, document_service.py, workspace_composer.py
│   │   ├── domain/           (project domain logic, validation)
│   │   ├── infrastructure/   (DB queries, repository pattern)
│   │   └── contracts/        ProjectSummaryContract, ProjectWorkspaceView
│   ├── agent/
│   │   ├── api/              router.py (existing agents router)
│   │   ├── application/      (agent orchestration)
│   │   ├── domain/           (agent domain: artifacts, state updates)
│   │   ├── infrastructure/   (tool implementations, LangGraph wiring)
│   │   └── contracts/        ConversationSummaryContract
│   ├── checklists/
│   │   ├── api/              checklist_router.py
│   │   ├── application/      checklist_service.py
│   │   ├── domain/           (checklist logic, WAF evaluation)
│   │   ├── infrastructure/   (DB, templates)
│   │   └── contracts/        (checklist summary contract)
│   ├── knowledge/
│   │   ├── api/              management_router.py, query_router.py
│   │   ├── application/      management_service.py, query_service.py
│   │   ├── domain/           (KB domain logic)
│   │   ├── infrastructure/   (KB index, embedding storage)
│   │   └── contracts/        KnowledgeContextContract
│   ├── ingestion/
│   │   ├── api/              router.py (existing ingestion router)
│   │   ├── application/      ingestion_service.py
│   │   ├── domain/           (pipeline logic)
│   │   ├── infrastructure/   (ingestion DB, file parsing)
│   │   └── contracts/        (ingestion status contract)
│   ├── diagrams/
│   │   ├── api/              (diagram generation endpoints)
│   │   ├── application/      diagram_generator.py, diagram_set_service.py
│   │   ├── domain/           (validation, compliance)
│   │   ├── infrastructure/   (diagram DB, rendering)
│   │   └── contracts/        DiagramSummaryContract
│   └── settings/
│       ├── api/              models_router.py
│       ├── application/      settings_service.py
│       └── contracts/        (settings contract)
├── shared/
│   ├── db/                   projects_database.py, base models, session helpers
│   ├── config/               app_settings.py, settings/
│   ├── ai/                   ai_service.py, providers/, interfaces.py, config.py
│   ├── mcp/                  MCP integration
│   ├── logging/              app_logging.py
│   └── container.py          DI container
├── agents_system/             (stays as platform orchestration — see C3)
│   ├── agents/
│   ├── langgraph/
│   ├── memory/
│   ├── config/
│   ├── runner.py
│   └── tools/                 (tool REGISTRATIONS only — implementations move to features)
├── main.py
├── lifecycle.py
└── service_registry.py
```

#### Task 3.1 — Create feature package scaffolding
- [x] Create directory structure for all 7 features: `projects`, `agent`, `checklists`, `knowledge`, `ingestion`, `diagrams`, `settings`
- [x] Each feature gets: `api/`, `application/`, `domain/`, `infrastructure/`, `contracts/`, `__init__.py`
- [x] Create `backend/app/shared/` with: `db/`, `config/`, `ai/`, `mcp/`, `logging/`
- [x] Add `__init__.py` files throughout

> **Delegation**: Subagent (execution) — directory creation script.

#### Task 3.2 — Move `shared/` infrastructure
- [x] Move `core/app_settings.py` → `shared/config/app_settings.py`
- [x] Move `core/settings/` → `shared/config/settings/`
- [x] Move `core/app_logging.py` → `shared/logging/app_logging.py`
- [x] Move `core/db.py` → `shared/db/db.py`
- [x] Move `projects_database.py` → `shared/db/projects_database.py`
- [x] Move `services/ai/` → `shared/ai/`
- [x] Move `services/mcp/` → `shared/mcp/`
- [x] Move `core/container.py` → `shared/container.py`
- [x] Keep `core/router_guardrails.py`, `core/signals.py` in `shared/` or `core/`
- [x] Update ALL imports across the entire backend
- [x] Run all tests: must pass
- [x] Run import-linter: must pass

Current branch note: the canonical platform packages now live under `shared/config`, `shared/db`, `shared/ai`, `shared/mcp`, `shared/runtime`, and `shared/http`. The former `core/` and top-level service-owned AI/MCP modules have been fully relocated, and runtime callers now import those shared packages directly.

> **Delegation**: Subagent `python-refactor` — provide the move map and ask for import updates. This is a high-risk move; do it in a dedicated branch.  
> **TDD**: Existing tests serve as regression suite. No new tests needed, but all must stay green.

#### Task 3.3 — Move projects feature
- [x] Move `routers/project_management/*` → `features/projects/api/`
- [x] Move `services/project/project_service.py` → `features/projects/application/`
- [x] Move `services/project/document_service.py` → `features/projects/application/`
- [x] Move `services/project/state_edit_service.py` → `features/projects/application/`
- [x] Move `services/project/project_analysis_service.py` → `features/projects/application/`
- [x] Move `services/project/proposal_stream_service.py` → `features/projects/application/`
- [x] Move `services/project/chat_service.py` → `features/projects/application/` (kept here for now; long-term ownership with `agent` remains deferred)
- [ ] Move `models/project.py` → `features/projects/infrastructure/models.py`
- [x] Update router registration in `main.py`
- [x] Update practical in-repo imports for the moved application services
- [x] Run focused backend tests for `backend/tests/features/projects`
- [x] **Verify**: external API routes unchanged (`/api/projects/...`)

Current branch note: the canonical projects service layer now lives in `features/projects/application/`, and the temporary `services/project/` facade has now been removed. Model relocation is still deferred.

> **Delegation**: Subagent `python-refactor`.  
> **TDD**: All existing project CRUD tests must pass unchanged.

#### Task 3.4 — Move agent feature
- [x] Move `routers/agents/` → `features/agent/api/`
- [x] Decide: does `agents_system/` stay as platform or move partially into `features/agent/`?
  - **Recommended**: `agents_system/` stays as platform. `features/agent/` owns the router and thin application service that calls into `agents_system/`.
- [x] Move agent-specific tool implementations into `features/agent/infrastructure/tools/`
  - `aaa_candidate_tool.py`, `aaa_artifacts_tool.py`, `aaa_cost_tool.py`, `aaa_iac_tool.py`, etc.
- [x] Keep tool registration/factory in `agents_system/tools/`
- [x] Update all imports
- [x] Run all existing agent/chat transport tests: must pass

Current branch note: `features/agent/api/` and `features/agent/application/` now own the canonical router, DTOs, and `AgentApiService`. `features/agent/infrastructure/tools/` now owns the AAA tool implementations, while `agents_system/tools/aaa_*.py` are compatibility wrappers and factory entrypoints only.

> **Delegation**: Subagent `python-refactor`.  
> **TDD**: All existing agent/chat tests must pass.

#### Task 3.5 — Move checklists feature
- [x] Move `routers/checklists/` → `features/checklists/api/`
- [x] Move `agents_system/checklists/` → `features/checklists/domain/` and `features/checklists/infrastructure/`
- [x] Move `models/checklist.py` → `features/checklists/infrastructure/models.py`
- [x] Update imports and router registration
- [x] Run all tests: must pass

Current branch note: `features/checklists/api/` owns the canonical router and schema modules, `features/checklists/{domain,infrastructure}` own the migrated checklist logic, and `features/checklists/infrastructure/models.py` is the canonical import surface over the existing checklist ORM mappings.

> **Delegation**: Subagent `python-refactor`.

#### Task 3.6 — Move knowledge feature
- [x] Move `routers/kb_management/` → `features/knowledge/api/`
- [x] Move `routers/kb_query/` → `features/knowledge/api/`
- [x] Move `services/kb/` → `features/knowledge/application/`
- [x] Move `kb/` → `features/knowledge/infrastructure/`
- [x] Update imports and router registration
- [x] Run all tests: must pass

Current branch note: `features/knowledge/api/` now owns the canonical KB management/query routers and Pydantic models, `features/knowledge/application/` now owns the canonical KB query/management services, and `features/knowledge/infrastructure/` now owns the canonical KB manager, KB config models, index service, and multi-query utilities. The legacy root service package has been removed; remaining compatibility cleanup is limited to non-service legacy package surfaces that were intentionally left for later slices.

> **Delegation**: Subagent `python-refactor`.

#### Task 3.7 — Move ingestion feature
- [x] Move `routers/ingestion/` → `features/ingestion/api/`
- [x] Move `services/ingestion/` → `features/ingestion/application/`
- [x] Move `ingestion/` → `features/ingestion/infrastructure/`
- [x] Update imports and router registration
- [x] Run all tests: must pass

Current branch note: `features/ingestion/api/` owns the canonical ingestion router and API models, `features/ingestion/application/` owns the ingestion orchestration/runtime/read-side services, and `features/ingestion/{domain,infrastructure}/` now own the canonical ingestion pipeline modules, repositories, schema, and persistence helpers. The root `services/` compatibility layer for ingestion has been removed; only the intentional top-level `app/ingestion/` package remains as the canonical feature package.

> **Delegation**: Subagent `python-refactor`.

#### Task 3.8 — Move diagrams feature
- [x] Move `routers/diagram_generation/` → `features/diagrams/api/`
- [x] Move `services/diagram/` → `features/diagrams/application/`
- [x] Move `models/diagram/` → `features/diagrams/infrastructure/models/`
- [x] Update imports and router registration
- [x] Run all tests: must pass

Current branch note: `features/diagrams/api/` owns the canonical diagram transport modules, `features/diagrams/application/` owns the canonical diagram service modules used by the router, startup/shutdown hooks, and project analysis flows, and `features/diagrams/infrastructure/models/` now owns the canonical SQLAlchemy diagram models. The legacy root diagram service package has been removed.

> **Delegation**: Subagent `python-refactor`.

#### Task 3.9 — Move settings feature
- [x] Move `routers/settings/` → `features/settings/api/`
- [x] Create thin `features/settings/application/settings_service.py` if needed
- [x] Update imports and router registration
- [x] Run all tests: must pass

Current branch note: `features/settings/api/` now owns the canonical settings router and `features/settings/application/settings_service.py` owns the canonical `SettingsModelsService`. The old root-level settings service shim has been removed.

> **Delegation**: Subagent `python-refactor`.

#### Task 3.10 — Define cross-feature contracts
- [x] Create `features/projects/contracts/project_summary.py`:
  ```python
  @dataclass
  class ProjectSummaryContract:
      project_id: str
      name: str
      description: str
      created_at: str
      document_count: int
  ```
- [x] Create `features/agent/contracts/conversation_summary.py`:
  ```python
  @dataclass
  class ConversationSummaryContract:
      project_id: str
      thread_id: str
      message_count: int
      last_message_at: str | None
  ```
- [x] Create `features/diagrams/contracts/diagram_summary.py`:
  ```python
  @dataclass
  class DiagramSummaryContract:
      project_id: str
      diagram_set_id: str
      diagram_count: int
      diagram_types: list[str]
  ```
- [x] Create `features/knowledge/contracts/knowledge_context.py`:
  ```python
  @dataclass
  class KnowledgeContextContract:
      kb_id: str
      name: str
      document_count: int
      status: str
  ```
- [x] Verify: no feature imports another feature's internals — only contracts
- [x] Run import-linter: must pass

Current branch note: this slice also introduced checklist and runtime-selection contracts to support `ProjectWorkspaceView`. `features/projects/application/` now consumes knowledge and diagram capabilities through adapters composed in `features/projects/api/_deps.py`, and `backend/tests/architecture/test_import_boundaries.py` plus `import-linter` both enforce that the projects application layer avoids other feature internals.

Additional branch note: `features/projects/contracts/project_summary.py` and `features/knowledge/contracts/knowledge_context.py` now exist as explicit cross-feature contracts and are covered by focused serialization tests.

> **Delegation**: Direct implementation — contracts are small dataclasses.  
> **TDD**: Write a test that verifies each contract can be instantiated and serialized.

#### Task 3.11 — Implement ProjectWorkspaceView and workspace composer
- [x] Define `ProjectWorkspaceView` in `features/projects/contracts/`:
  ```python
  @dataclass
  class ProjectWorkspaceView:
      project: ProjectSummaryContract
      inputs: dict          # architecture inputs from state
      documents: list[dict] # project documents
      chat: dict            # conversation summary
      checklists: list[dict]
      diagrams: dict        # diagram summary
      artifacts: dict       # ADRs, findings, cost, IaC summaries
      metadata: dict        # timestamps, version
  ```
- [x] Create `features/projects/application/workspace_composer.py`:
  - Composes `ProjectWorkspaceView` by calling each feature's contract provider
  - Falls back to legacy JSON state for any non-migrated artifact family
- [x] Add `GET /api/projects/{project_id}/workspace` endpoint in projects router
- [x] Make `GET /api/projects/{project_id}/state` internally call workspace composer (compatibility)
- [ ] Write tests:
  - [x] Happy path: full workspace view with all sections
  - [x] Legacy fallback: project with only JSON state, no feature-owned stores
  - [x] Mixed: some artifacts migrated, some still in JSON
- [x] Run targeted workspace tests: must pass

Current branch note: the backend workspace contract is now structured around explicit `inputs`, `documents`, and `artifacts` sections rather than a raw `projectState` payload. The deprecated `/state` endpoint still projects that structured view back into the legacy shape for compatibility, while the frontend adapts the structured `/workspace` response locally. Workspace-specific dependency adapters now live in `backend/app/features/projects/api/workspace_dependencies.py` so `projects/api/_deps.py` only delegates assembly, and the unified frontend shell now renders through `frontend/src/features/projects/workspaceShellRegistry.tsx` instead of hard-wiring the header, left tree, center tabs, and chat panel inside `UnifiedProjectWorkspace.tsx`.

Follow-up branch note: the remaining migration seams on the backend are now narrowed further. Shared runtime session helpers no longer import the legacy `app.ingestion` package, runtime KB access in `agents_system/agents/rag_agent.py` and `projects/api/_deps.py` now goes through dependency providers instead of importing `app.service_registry` directly, and the backend architecture workflow now validates the current workspace/state contracts via dedicated composer/state projection tests plus the updated document-analysis smoke test.

> **Delegation**: Subagent `python-refactor` for implementation. Write tests first (TDD).

#### Task 3.12 — Update import-linter rules for new structure
- [x] Update `.importlinter` contracts to reflect the features/ layout
- [x] Add independence contracts between all features
- [x] Add layer contracts within each feature (api → application → domain ← infrastructure)
- [x] Verify: `import-linter` passes on the full codebase
- [x] Promote to blocking in CI

Current branch note: the backend rule set now includes feature API independence, per-feature layer contracts, the checklist legacy-package ban, and the legacy AI/MCP/core shim ban. The full backend import-linter run is green and the architecture workflow now runs it as a blocking check.

> **Delegation**: Subagent (execution) — run import-linter, fix violations iteratively.

---

### Phase 4 — ProjectState Decomposition

**Goal**: Migrate artifact families out of the JSON blob into feature-owned tables.

#### Implementation Note — 2026-04-02

- This branch now uses a two-part decomposed storage model for `ProjectState`: `project_architecture_inputs` for the architecture-input family and `project_state_components` for the remaining stable top-level artifact families.
- Canonical reads (`read_project_state`) compose the compatibility blob with both decomposed stores, opportunistically backfill missing component rows from legacy blob data, and prefer normalized checklist rows over legacy `wafChecklist` blob payloads when they exist.
- Canonical writes now sync both decomposed stores and strip those keys from new `project_states.state` writes in the main state update, document-analysis, chat persistence, ADR append, and diagram-reference append flows.
- Historical rows can be backfilled with `uv run python scripts/migrate_arch_inputs.py` and `uv run python scripts/migrate_project_state_components.py`; `--prune-blob` remains optional for explicit cleanup passes.
- Residual legacy behavior is now narrow: `ProjectState.state` remains a compatibility/cache blob for unknown historical keys and for legacy `wafChecklist` payloads when a project has not yet been normalized into checklist rows.

#### Prerequisite: Complete Task 0.4 (audit) to know exactly what's in the blob.

Based on the current frontend type definitions, the JSON blob likely contains:
1. `context` (summary, objectives, target users, scenario type)
2. `nfrs` (availability, security, performance, cost constraints)
3. `applicationStructure` (components, integrations)
4. `dataCompliance` (data types, requirements, residency)
5. `technicalConstraints` (constraints, assumptions)
6. `openQuestions`

Plus agent-written artifacts such as requirements, assumptions, clarification questions, candidate architectures, ADRs, findings, diagrams, cost estimates, IaC, traceability links/issues, mind-map projections, reference documents, MCP queries, iteration events, and analysis metadata.

#### Migration pattern (repeat for each artifact family):
1. **Alembic migration**: create new table
2. **Backfill script**: read JSON blob → insert into new table
3. **Dual-read adapter**: read from new table, fall back to JSON blob
4. **Write-path switch**: new writes go to table, not JSON blob
5. **Verification test**: compare old reads vs new reads for parity
6. **Old write-path removal**: delete JSON write code

#### Task 4.1 — Migrate architecture inputs to dedicated table
- [x] Create Alembic migration: dedicated architecture-input table (`project_architecture_inputs`)
  ```
  project_id (PK, FK), summary, objectives (JSON), target_users,
  scenario_type, nfrs (JSON), components (JSON), integrations (JSON),
  data_compliance (JSON), technical_constraints (JSON), open_questions (JSON),
  updated_at
  ```
- [x] Write backfill script: `scripts/migrate_arch_inputs.py`
- [x] Create `features/projects/infrastructure/architecture_inputs_repository.py`
- [x] Update state persistence to write architecture inputs to the new table and strip them from new blob writes where practical
- [x] Update workspace composer and canonical state reads to prefer the new table, fallback to JSON
- [x] Write parity tests: legacy-only, decomposed-only, and mixed state reads preserve workspace/state behavior
- [x] Run targeted backend tests covering the decomposition slice

Implemented schema note: the dedicated table stores each architecture-input family as JSON text per top-level key (`context`, `nfrs`, `applicationStructure`, `dataCompliance`, `technicalConstraints`, `openQuestions`) to preserve current payload parity while moving ownership out of `ProjectState.state`.

> **Delegation**: Subagent (execution) for Alembic migration and backfill. Subagent `python-refactor` for service/repository code.  
> **TDD**: Write parity test first.

#### Task 4.2 — Migrate remaining artifact families via generic component store
- [x] Confirm via audit (Task 0.4) that the remaining agent/workspace artifact families are actually in JSON blob
- [x] Add additive storage for the remaining stable top-level families via `project_state_components`
- [x] Add dual-read behavior with opportunistic backfill from legacy blob rows into `project_state_components`
- [x] Redirect canonical write paths to sync the component store and strip those families from new blob writes
- [x] Cover the new storage model with focused read/write regression tests

Implemented families in the generic component store: `requirements`, `assumptions`, `clarificationQuestions`, `candidateArchitectures`, `adrs`, `findings`, `diagrams`, `iacArtifacts`, `costEstimates`, `traceabilityLinks`, `traceabilityIssues`, `mindMapCoverage`, `mindMap`, `referenceDocuments`, `mcpQueries`, `iterationEvents`, `analysisSummary`, and `projectDocumentStats`.

> **Delegation**: Same pattern as 4.1.

#### Task 4.3 — ADR/direct-helper parity cleanup
- [x] Keep the ADR append helper working when the compatibility blob no longer owns `adrs`
- [x] Verify direct helper writes resync the generic component store instead of rehydrating ADRs back into the blob

> **Delegation**: Same pattern as 4.1.

#### Task 4.4 — Findings / traceability parity
- [x] Findings and traceability data now persist through the generic component store on canonical state updates
- [ ] Family-specific tables remain deferred unless query patterns or lifecycle needs justify splitting them out later

#### Task 4.5 — Migrate cost estimates (if in JSON blob)
- [x] Cost estimates now persist through the generic component store on canonical state updates
- [ ] Family-specific pricing storage remains deferred unless downstream reads need dedicated indexing/query support

#### Task 4.6 — Migrate IaC bundles (if in JSON blob)
- [x] IaC artifacts now persist through the generic component store on canonical state updates
- [ ] A specialized IaC table remains deferred until artifact versioning/export requirements justify it

#### Task 4.7 — Migrate traceability links (if in JSON blob)
- [x] Traceability links/issues now persist through the generic component store on canonical state updates
- [ ] Further ownership cleanup is still needed if traceability becomes independently queryable outside the composed state view

---

### Phase 5 — Legacy Removal and Stabilization

**Goal**: Remove legacy write paths, reduce `ProjectState` to read/cache only, final cleanup.

#### Task 5.1 — Remove JSON blob write paths
- [x] Remove canonical blob writes for the architecture-input family and the remaining stable top-level artifact families owned by `project_state_components`
- [x] Keep `ProjectState` as a compatibility/cache blob for legacy unknown keys and staged cleanup
- [x] Update decomposition regression tests for the reduced blob role

Current branch status: the blob is no longer the canonical store for architecture inputs or the major AAA/workspace artifact families. The remaining irreducible legacy fallback is `wafChecklist` blob data for projects that have not yet been reconstructed from normalized checklist rows, plus any unknown historical keys outside the owned decomposition set.

> **Delegation**: Subagent `python-refactor`.

#### Task 5.2 — Deprecate `/api/projects/{id}/state` endpoint
- [x] Add deprecation header to response
- [x] Update frontend to call `/api/projects/{id}/workspace` instead
- [x] Set removal timeline (e.g., 2 releases after migration complete)

Current branch note: the endpoint now returns `Deprecation`, `Sunset`, and `Link` headers pointing callers at `/api/projects/{project_id}/workspace`, and the frontend's canonical state loaders now read the `projectState` payload from `/workspace`.

> **Delegation**: Direct edit.

#### Task 5.3 — Remove empty old directories
- [x] Remove `backend/app/routers/` (if fully moved to features)
- [x] Remove `backend/app/services/` (if fully moved to features/shared)
- [x] Remove `backend/app/core/` (if fully moved to shared)
- [x] Update any remaining imports
- [x] Run all tests: must pass

Current backend note: this pass removes `backend/app/core/`, `backend/app/routers/`, and `backend/app/services/` completely after moving their last live helpers into `app.shared.*` and `app.features.*` packages, repointing all remaining imports, and updating the architecture gates to enforce the new shape.

Frontend branch note: this slice removed the remaining root `frontend/src/{hooks,services,types}` compatibility shims, deleted the obsolete `ArtifactViews.tsx` workspace tab dispatcher, and moved static project tab rendering behind `frontend/src/features/projects/workspaceTabRegistry.tsx`. No root hook, service, or type shim remains in the frontend tree.

> **Delegation**: Subagent (execution).

#### Task 5.4 — Final CI hardening
- [x] Promote all architecture checks to blocking
- [x] Remove warning/allow-failure flags
- [x] Add check: new files under `features/` must be in a known feature directory
- [x] Add check: `agents_system/tools/` only contains registration/factory code, not implementations

Current backend note: `.github/workflows/architecture.yml` now runs the real `backend/tests/architecture` suite, the strengthened `import-linter` contract set, and the horizontal freeze check as blocking jobs. The backend architecture tests also enforce the curated backend/frontend feature directory sets and require `agents_system/tools/aaa_*.py` to remain compatibility wrappers over feature-owned implementations.

Frontend branch note: the ESLint boundary rule now hard-fails root compatibility-shim imports (`services`, `hooks`, `types`, `config`, and `utils`) across the feature tree, while the targeted projects/knowledge override still keeps a dedicated error message for the removed root `types/api` aggregate. Frontend import normalization is complete for the former root shim layer.

Verification note: the blocking workflow now uses the repo-root Vitest architecture command (`npx vitest run --pool=forks frontend/src/architecture/import-boundaries.test.ts`) because it is the stable invocation in this repo, while the backend gates run `backend/tests/architecture`, `lint-imports`, and the horizontal freeze check.

Current ownership note: the projects workspace shell and static tab registry now compose feature-contributed tab definitions and renderers from smaller contributor modules instead of one monolithic registry file, and the repository now includes `.github/CODEOWNERS` aligned with the lane map.

> **Delegation**: Subagent (execution).

#### Task 5.5 — Documentation update
- [x] Update `docs/README.md` with new architecture references
- [x] Update `docs/architecture/system-architecture.md` with feature model
- [x] Update `docs/backend/BACKEND_REFERENCE.md` with current decomposition and endpoint status
- [x] Update `docs/frontend/FRONTEND_REFERENCE.md` with new layout
- [x] Update `docs/agents/` with architecture changes
- [x] Create `docs/architecture/FEATURE_DEVELOPMENT_GUIDE.md`:
  - How to add a new feature
  - How to add a workspace tab
  - How to define a contract
  - How to register a tool in agents_system

Current branch note: this pass updates the backend, frontend, architecture, and agent-lane docs to match the current feature/shared layout, workspace registry, and `/workspace`-first state model.

> **Delegation**: Subagent `speckit.plan` or direct edit.

---

## Test Plan Summary

| Test Category | When Added | Blocking? |
|---|---|---|
| Architecture import boundary tests (backend) | Phase 1 | Yes (after Phase 3) |
| Architecture import boundary tests (frontend) | Phase 1 | Yes (after Phase 2) |
| ProjectWorkspaceView unit tests | Phase 3 | Yes |
| Legacy ProjectState compatibility tests | Phase 3 | Yes |
| Artifact migration parity tests | Phase 4 (per family) | Yes |
| Existing flow tests (project CRUD, chat, etc.) | Already exist | Yes (always) |
| Collaboration scenario tests | Phase 5 | Yes |

---

## Shim Retirement Progress

The following legacy compatibility shim packages have been fully retired:

| Package | Retired | Replacement | Import-linter contract |
|---|---|---|---|
| `app.kb/` (5 modules) | 2026-04-07 | `app.features.knowledge.infrastructure` | `retired-kb-shim` |
| `app.models.diagram/` (6 modules) | 2026-04-07 | `app.features.diagrams.infrastructure.models` | `retired-diagram-model-shim` |
| `app.ingestion.ingestion_schema` (duplicate code) | 2026-04-07 | Re-export from `app.features.ingestion.infrastructure.ingestion_schema` | — |

Deprecated dead code removed:
- `_deep_merge()` in `app.agents_system.services.project_context` (superseded by `merge_state_updates_no_overwrite`)

Additional fixes:
- `set_model()` in `SettingsModelsService` simplified to delegate to `set_selection()` (eliminates duplicate chat-probe path and stale `ChatMessage` reference)

Import-linter contract count: **19 contracts** (up from 17).

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Import breakage during mass file moves | High | Medium | Do one feature at a time, run full test suite after each move |
| agents_system breaks after tool moves | Medium | High | Move tool implementations last, keep registration in agents_system |
| Frontend TypeScript errors after restructure | High | Low | TypeScript compiler catches all import errors at build time |
| Data loss during JSON blob migration | Low | Critical | Backfill scripts are idempotent, dual-read adapter verifies parity |
| CI architecture checks too strict | Medium | Low | Start in warning mode, promote to blocking after validation |
| Scope creep — refactoring code during moves | High | Medium | Strict rule: moves only change file paths and imports, never logic |

---

## Success Criteria

1. **Feature isolation**: most feature work happens inside one `features/<name>/` folder on both backend and frontend.
2. **No cross-feature imports**: import-linter and ESLint enforce boundaries; CI blocks violations.
3. **Workspace extensibility**: adding a new workspace tab requires changes only in the owning feature + manifest registration.
4. **Backward compatibility**: all existing API routes and user-visible flows work unchanged.
5. **ProjectState retired**: no new writes to JSON blob; workspace composer assembles from feature-owned stores.
6. **Test coverage maintained**: existing test suite passes at every phase boundary.

---

## Dependency Graph

```
Phase 0 (governance) ──────────────────────────────────────────────────┐
    │                                                                  │
    ├── Task 0.4 (audit JSON blob) ── required by ── Phase 4          │
    │                                                                  │
Phase 1 (CI enforcement) ─── can start after Phase 0 ─────────────────┤
    │                                                                  │
Phase 2 (frontend carve-out) ─── can start after Phase 1 ─────────────┤
    │                                                                  │
Phase 3 (backend carve-out) ─── can start after Phase 1 ──────────────┤
    │                          ─── Phase 2 NOT required (parallel OK)  │
    │                                                                  │
Phase 4 (ProjectState decomp) ─── requires Phase 3 + Task 0.4 ────────┤
    │                                                                  │
Phase 5 (legacy removal) ─── requires Phase 4 ────────────────────────┘
```

**Key parallelism**: Phase 2 and Phase 3 can run in parallel after Phase 1 is done. This means frontend and backend carve-outs can be delegated to different subagents simultaneously.
