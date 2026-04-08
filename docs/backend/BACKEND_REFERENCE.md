# Backend Reference

## Entry points and layout

- App entry: `backend/app/main.py`
- Lifecycle: `backend/app/lifecycle.py`
- Router facade and remaining unmigrated router packages: `backend/app/routers/`
- Canonical agent HTTP surface: `backend/app/features/agent/api/`
- Canonical checklist HTTP surface: `backend/app/features/checklists/api/`
- Canonical diagrams HTTP surface: `backend/app/features/diagrams/api/`
- Canonical ingestion HTTP surface: `backend/app/features/ingestion/api/`
- Canonical ingestion pipeline ownership: `backend/app/features/ingestion/{application,domain,infrastructure}/`
- Canonical knowledge HTTP surface: `backend/app/features/knowledge/api/`
- Canonical projects HTTP surface: `backend/app/features/projects/api/`
- Canonical settings HTTP surface: `backend/app/features/settings/api/`
- Services: `backend/app/services/` (mixed canonical services plus compatibility shims for moved feature-owned services)
- Legacy ingestion compatibility package: `backend/app/ingestion/` (ingestion_schema.py is a re-export shim delegating to the canonical feature module)
- Agent system: `backend/app/agents_system/`
- Agent nodes: `backend/app/agents_system/langgraph/nodes/` (core), `nodes/routing/` (per-agent routing)
- Diagram generation: `backend/app/services/diagram/`
- SQLAlchemy models: `backend/app/models/` plus feature-owned infrastructure models (diagram models live canonically under `backend/app/features/diagrams/infrastructure/models/`; the `app.models.diagram` shim package was retired)

## Router conventions

- KB management and query routes now live canonically under `app.features.knowledge.api`; the corresponding orchestration/query services live canonically under `app.features.knowledge.application`; and the former `app.kb` package now lives canonically under `app.features.knowledge.infrastructure`. The `app.kb` shim package has been retired and import-linter enforces that it cannot be re-introduced. The top-level `app.routers` facade still exports `kb_management_router` and `kb_query_router`, while `routers/kb_management/`, `routers/kb_query/`, and `services/kb/` remain compatibility shims.
- Agent routes now live canonically under `app.features.agent.api`; the top-level `app.routers` facade still exports `agent_router`, but it now resolves directly to that feature package instead of `routers/agents/`.
- Checklist routes now live canonically under `app.features.checklists.api`; the legacy `routers/checklists/` package is a compatibility shim.
- Diagram routes now live canonically under `app.features.diagrams.api`; diagram services live canonically under `app.features.diagrams.application`; diagram SQLAlchemy models now live canonically under `app.features.diagrams.infrastructure.models`. The `app.models.diagram` shim package has been retired and import-linter enforces that it cannot be re-introduced. The legacy `routers/diagram_generation/` and `services/diagram/` packages remain compatibility shims.
- Ingestion routes now live canonically under `app.features.ingestion.api`; ingestion orchestration, runtime, read-side helpers, domain pipeline components, repositories, schema, and ingestion persistence helpers now live canonically under `app.features.ingestion.{application,domain,infrastructure}`; the legacy `routers/ingestion/` package, `services/ingestion_metrics_service.py`, `services/ingestion_read_service.py`, `services/ingestion_runtime.py`, and top-level `app.ingestion` package remain compatibility shims.
- Projects routes now live canonically under `app.features.projects.api`; the top-level `app.routers` facade still exports `project_router`, but it now resolves directly to that feature package instead of a legacy `routers/project_management/` shim package.
- Settings routes now live canonically under `app.features.settings.api`; the legacy `routers/settings/` package is a compatibility shim.

## API overview

### Health
- `GET /health` - service health.

### Projects
- `POST /api/projects`
- `GET /api/projects`
- `GET /api/projects/{project_id}`
- `PUT /api/projects/{project_id}/requirements`
- `POST /api/projects/{project_id}/documents`
- `GET /api/projects/{project_id}/documents/{document_id}/content` - returns the stored uploaded file when available; if the binary path is stale, probes historical/current storage layouts; if a PDF binary is still missing but `documents.raw_text` was persisted, regenerates a PDF under the canonical current storage root so the document remains downloadable/renderable; non-PDF documents fall back to an inline HTML preview built from extracted text
- `POST /api/projects/{project_id}/analyze-docs`
- `POST /api/projects/{project_id}/chat`
- `GET /api/projects/{project_id}/state` - legacy compatibility read, now returned with deprecation headers and a successor link to the workspace view
- `GET /api/projects/{project_id}/workspace` - canonical composed workspace read spanning project, state summary, full composed `projectState`, agent, checklist, KB, diagram, and runtime sections
- `GET /api/projects/{project_id}/messages`
- `GET /api/projects/{project_id}/changes` - read-only pending change-set summaries projected from `projectState.pendingChangeSets`; supports an optional `status` filter.
- `GET /api/projects/{project_id}/changes/{change_set_id}` - read-only pending change-set detail, including artifact drafts and proposed patch payload.
- `POST /api/projects/{project_id}/changes/{change_set_id}/approve` - approves a pending change set, merges its `proposedPatch` into canonical project state, and returns the reviewed change set plus updated state.
- `POST /api/projects/{project_id}/changes/{change_set_id}/reject` - marks a pending change set rejected without mutating canonical project state.
- `POST /api/projects/{project_id}/changes/{change_set_id}/revise` - marks a pending change set superseded so a revised bundle can replace it later.
- `POST /api/projects/{project_id}/extract-requirements` - loads parsed project documents, runs the Phase 4 extraction worker, and records a pending requirements change set for review.
- `GET /api/projects/{project_id}/architecture/proposal` (SSE)

### Knowledge base management
- `POST /api/kb/create`
- `GET /api/kb/list`
- `GET /api/kb/health`
- `GET /api/kb/{kb_id}/status`
- `DELETE /api/kb/{kb_id}`

### Ingestion (orchestrator)
- `POST /api/ingestion/kb/{kb_id}/start`
- `POST /api/ingestion/kb/{kb_id}/pause`
- `POST /api/ingestion/kb/{kb_id}/resume`
- `POST /api/ingestion/kb/{kb_id}/cancel`
- `GET /api/ingestion/kb/{job_id}/status`
- `GET /api/ingestion/kb/{kb_id}/details`
- `GET /api/ingestion/kb/{kb_id}/job-view`

### KB queries
- `POST /api/query` (legacy)
- `POST /api/query/chat`
- `POST /api/query/proposal`
- `POST /api/query/kb-query`

### Agent chat
- `POST /api/agent/chat`
- `POST /api/agent/projects/{project_id}/chat`
- `GET /api/agent/projects/{project_id}/history`
- `GET /api/agent/health`
- `GET /api/agent/capabilities`

### Diagram generation
- `POST /api/diagram-sets`
- `GET /api/diagram-sets/{diagram_set_id}`

## Data models (high level)

- Project: name, requirements, created/updated timestamps.
- Project state: mixed compatibility blob + composed reads. Architecture inputs live in `project_architecture_inputs`, most remaining top-level artifact families live in `project_state_components`, normalized checklist rows are the preferred source for `wafChecklist`, and the initial Phase 3 approval scaffold reads/writes `pendingChangeSets` from the recomposed compatibility payload without changing the current agent mutation path yet.
- Knowledge base: config in `data/knowledge_bases/config.json` with per-KB settings.
- Diagram set: input description, diagrams, ambiguities, stored in `data/diagrams.db`.

## ProjectState decomposition status

- Dedicated architecture-input persistence now lives in `backend/app/models/project.py` as `ProjectArchitectureInputs` (`project_architecture_inputs` table).
- Dedicated generic artifact persistence now lives in `backend/app/models/project.py` as `ProjectStateComponent` (`project_state_components` table), keyed by `project_id + component_key`.
- Canonical read path: `app.agents_system.services.project_context.read_project_state(...)` composes the compatibility blob with `project_architecture_inputs`, `project_state_components`, and normalized checklist rows, then applies AAA normalization and document-derived metadata.
- Deterministic Phase 8 checklist evaluation now lives in `app.agents_system.services.waf_evaluator.WAFEvaluatorService`, which inspects recomposed project state and emits structured WAF coverage summaries for later validate-stage workers.
- Canonical workspace read path: `app.features.projects.application.workspace_composer.ProjectWorkspaceComposer` now receives recomposed state from the canonical state provider; the remaining direct architecture-input repository call is compatibility-only and does not own the rest of state composition.
- `/api/projects/{project_id}/workspace` now returns the full recomposed `projectState` payload alongside the workspace summary sections, and the deprecated `/api/projects/{project_id}/state` route now sources that payload from the same composer for compatibility.
- Canonical write paths for the owned decomposed families now sync the dedicated stores and strip those keys from new blob writes in:
    - `app.agents_system.services.project_context.update_project_state(...)`
    - `app.services.project.document_service.DocumentService.analyze_documents(...)`
    - `app.services.project.chat_service.ChatService.process_chat_message(...)`
    - Compatibility-path cleanup on other legacy rewrites (`upload_documents`, ADR append, diagram-ref append, project delete diagram cleanup)
- Backfill support:
    - `uv run python scripts/migrate_arch_inputs.py` copies legacy architecture-input keys from `project_states.state` into `project_architecture_inputs`
    - `uv run python scripts/migrate_project_state_components.py` copies remaining owned top-level families from `project_states.state` into `project_state_components`
    - Use `--prune-blob` only when you explicitly want to remove migrated keys from historical blob rows.
- Residual exceptions: `ProjectState.state` can still hold unknown historical keys and legacy `wafChecklist` payloads for projects that have not yet been normalized into checklist rows. Those cases are compatibility fallbacks, not the preferred canonical store.

## Configuration and settings

- `.env` (repo root) provides ports, API keys, and storage paths.
- `backend/app/shared/config/app_settings.py` is the canonical runtime configuration entry point (use `get_app_settings()`).
- `backend/app/core/app_settings.py` remains only as a backward-compatible import target for out-of-tree callers; in-repo app code, migrations, and scripts now import `backend/app/shared/config/app_settings.py` directly.
- Add or change env-backed settings in settings mixins under `backend/app/core/settings/`, then consume through `AppSettings`.
- Shared logging and projects-database session helpers now resolve directly from `app.shared.logging.app_logging` and `app.shared.db.projects_database`; the old `app.core.app_logging`, `app.core.container`, `app.core.db`, and `app.projects_database` shim modules were removed in the final backend hardening pass.
- `backend/config/ingestion.config.json` and `backend/config/kb_defaults.json` are file-backed defaults loaded by `IngestionSettingsMixin` into `AppSettings` (`ingestion_queue`, `kb_defaults`).
- `backend/config/mcp/mcp_config.json` is loaded through `AppSettings.get_mcp_server_config(...)`.
- Storage paths come through `AppSettings`; relative values from process env or `.env` resolve against `backend/`. The fallback data root is `backend/data`, which covers `projects.db`, `ingestion.db`, and the `knowledge_bases/` directory.
- `SettingsModelsService` validates `PUT /api/settings/llm-selection` against provider model listings and persists the selection to `runtime_ai_selection.json`; it does not require a live chat completion probe to accept a listed model.
- `backend/config/prompts/*.yaml` and `backend/config/checklists/*.json` are content/resource files (not env settings) loaded by dedicated services. `PromptLoader.compose_prompt(agent_type, stage, context_budget)` now assembles modular prompt fragments (`base_persona`, agent-specific routing, stage-specific instructions, tool strategy, guardrails) and falls back to `agent_prompts.yaml` when modular files are absent.
- Agent runtime is LangGraph-only (legacy LangChain ReAct backend paths were removed).
- AI provider routing and fallback behavior is documented in `docs/backend/AI_PROVIDER_ROUTING.md`.

## Remaining compatibility paths

- `app.core.app_settings` is retained only as a backward-compatible import target for out-of-tree callers; backend packages, migrations, and scripts now resolve through `app.shared.config.app_settings`.
- `/api/projects/{project_id}/state` remains a deprecated compatibility read layered on top of the workspace composer; `/api/projects/{project_id}/workspace` is the canonical composed read surface used by current frontend state loaders.
- `ProjectState.state` remains a compatibility/cache blob for unknown historical keys and legacy `wafChecklist` payloads on projects that have not yet been reconstructed from normalized checklist rows.

## Singleton Pattern Usage

The backend uses singletons for expensive, shared resources with lifecycle management needs.

### Current Singletons

| Service | Location | Justification | Performance Impact |
|---------|----------|---------------|-------------------|
| **AgentRunner** | `app/agents_system/runner.py` | Lifecycle coordination for shared MCP/OpenAI runtime context used by LangGraph nodes | Startup: 2-3s (MCP + LLM init) |
| **KBManager** | `app/service_registry.py` | Vector index caching (150MB in memory), preloaded at startup | 3.2s load time per KB, indices cached in memory |
| **LLMService** | `app/services/llm_service.py` | Connection pooling to OpenAI/Azure | HTTP client reuse, rate limiting |
| **AIService** | `app/services/ai/ai_service.py` | Provider abstraction (OpenAI, Azure, Anthropic) | Model caching, connection pooling |
| **PromptLoader** | `app/agents_system/config/prompt_loader.py` | File I/O caching for YAML prompts | Avoids repeated disk reads |

### Accessing Singletons

**✅ Recommended**: Use FastAPI dependency injection for testability:

```python
from fastapi import Depends
from app.dependencies import get_kb_manager

@router.get("/kbs")
async def list_kbs(kb_manager: KBManager = Depends(get_kb_manager)):
    return kb_manager.list_kbs()
```

**❌ Avoid**: Direct singleton access (harder to test):

```python
# Don't do this in routes
kb_manager = ServiceRegistry.get_kb_manager()
```

### Testing with Singletons

All singletons support dependency override for testing:

```python
from app.dependencies import get_kb_manager

def test_my_route(client, mock_kb_manager):
    app.dependency_overrides[get_kb_manager] = lambda: mock_kb_manager
    # ... test code ...
    app.dependency_overrides.clear()
```

See [Testing Guide](backend/TESTING_DEPENDENCY_INJECTION.md) for comprehensive examples.

### Design Rationale

See [Singleton Pattern Analysis](reviews/SINGLETON_PATTERN_ANALYSIS.md) for detailed architectural rationale and alternatives considered.

**Key Benefits**:
- **Performance**: 150MB indices loaded once, not per-request (100 req/min = 320s CPU without singleton)
- **Lifecycle**: Coordinated startup/shutdown prevents resource leaks
- **Consistency**: All requests see same runtime context (KB updates, agent runtime state)
- **Testability**: FastAPI dependency injection enables easy mocking


## Adding a new backend feature

1. Decide the feature area (projects, agent, KB, ingestion, diagrams) and create a router module under `backend/app/features/<feature>/api/`.
2. Define request/response models (Pydantic) near the router or in a `*_models.py` file.
3. Implement business logic in a service module (avoid router-local operations modules).
4. Register the router in `backend/app/main.py` or the `backend/app/routers/` facade if the compatibility export still exists.
5. Add or update frontend calls in `frontend/src/services/apiService.ts` and align types.

## Adding or changing persistence

- Add SQLAlchemy models in `backend/app/models/`.
- Create or update Alembic migrations in `backend/migrations/`.
- Update any service code that reads/writes the new tables.

## Extending ingestion

- Add a source handler in `backend/app/features/ingestion/domain/sources/` and register it in `factory.py`.
- Update KB configuration to include the new source type.
- If the UI needs new fields, update `frontend/src/utils/ingestionConfig.ts`.

## Agent system module layout

- `langgraph/graph_factory.py` — Project chat graph assembly; stage routing resolves before context summary/context-pack construction so stage-specific compaction sees the routed stage, `extract_requirements` has a dedicated runtime node, and `propose_candidate` now routes through a dedicated research-worker → architecture-planner slice before the generic agent path.
- `config/prompt_loader.py` — YAML prompt loader; supports both the legacy `agent_prompts.yaml` surface and modular prompt composition for stage-aware orchestrator prompts.
- `memory/context_packs/stage_packers.py` — Stage-specific compaction builders; ADR packs read canonical `adrs`, and validation packs summarize `wafChecklist.items[*].evaluations[*].status` from the current checklist payload.
- `nodes/stage_routing.py` — Core stage enum, classification, retry logic. When parsed project documents exist but approved requirements are still missing, the state-aware default now routes to `extract_requirements` before falling back to clarification.
- `nodes/agent_native.py` — Native LangGraph orchestrator node; builds system directives from the composed stage-aware prompt surface.
- `features/projects/application/pending_changes_service.py` — Read-side projection for `pendingChangeSets`, providing typed summaries/details without changing persistence semantics yet.
- `features/projects/application/pending_changes_merge_service.py` — Deterministic approval merge helper built on the existing non-overwrite state merge behavior; conflicts surface as 409s instead of silently overwriting canonical state.
- `features/projects/api/changes_router.py` — Project-scoped pending change-set read and review endpoints.
- `features/agent/contracts/extract_requirements.py` — Strict contracts for source-grounded extracted requirements, ambiguity markers, and bundle summaries.
- `features/agent/application/adr_lifecycle_service.py` — Deterministic ADR lifecycle helper for draft/create, reject, accept, and supersede transitions; normalizes ADR payloads and refreshes traceability links so later stage workers can mutate `projectState.adrs` without router-specific logic.
- `features/agent/application/requirements_extraction_service.py` — Exact-match requirement dedupe/bundling helper that preserves all document sources and rolls ambiguity notes forward.
- `features/agent/application/requirements_extraction_worker.py` — First Phase 4 worker path; formats parsed project documents for analysis, normalizes extracted requirements, builds a pending change set, and records it through the pending-change service.
- `features/projects/application/requirements_extraction_entry_service.py` — Project-scoped DB/document-loading entry point for requirements extraction; feeds parsed documents to the worker and returns the recorded pending change set.
- `nodes/routing/` — Per-agent routing subpackage (architecture_planner, iac_generator, saas_advisor, cost_estimator, `_helpers.py` for shared utils).
- `nodes/extract_requirements.py` — Dedicated Phase 4 stage worker; executes the requirements extraction entry service inside the graph, records a pending requirements bundle, refreshes project state, and emits a review-focused response without invoking the general LLM path.
- `nodes/research.py` — Phase 6 research-planning/runtime helper; turns research plans into concrete evidence packets and records a deterministic execution artifact before architecture synthesis.
- `nodes/architecture_planner.py` — Dedicated architecture synthesizer for `propose_candidate`; consumes the research-worker handoff packets alongside requirements/NFR context.
- `nodes/agent.py` — Main agent node entry (`run_agent_node`) for non-`extract_requirements` stage execution and guardrail shortcuts.
- `nodes/scope_guard.py` — Scope-detection patterns and guardrails.
- `nodes/waf_shortcuts.py` — Deterministic WAF-checklist shortcut handlers.
- `services/waf_evaluator.py` — Deterministic Phase 8 evaluator; scans recomposed architecture evidence (including ADRs and reference documents) and returns worker-friendly per-item WAF coverage with summary counts.
- `services/diagram/project_diagram_helpers.py` — Diagram business logic extracted from project_router.
- `services/project/document_normalization.py` — Requirements/questions normalization helpers.

## Evaluation and E2E harness

- `scripts/e2e/aaa_e2e_runner.py` — Canonical end-to-end AAA scenario runner; replays scenario chat turns against the agent API, records advisory/tool usage signals, and manages normalized goldens under `scripts/e2e/goldens/`.
- `scripts/e2e/scenarios/` — Golden scenario inputs used to baseline AAA behavior across requirements, architecture, ADR, validation, IaC, cost, and traceability flows.
- `backend/tests/eval/reporting.py` — Typed Phase 0 evaluation summary layer that converts the existing E2E runner report shape into rubric-friendly scenario/turn summaries for regression tracking.

## AAA ProjectState tools

All AAA tools live in `backend/app/agents_system/tools/` and are registered by `create_aaa_tools()` in `aaa_candidate_tool.py`.  Each tool emits `AAA_STATE_UPDATE` (or `AAA_EXPORT`) JSON blocks that the state-update parser (`state_update_parser.py`) picks up during the postprocess node.

| Tool | File | Purpose |
|------|------|---------|
| `aaa_generate_candidate_architecture` | `aaa_candidate_tool.py` | Persist candidate architectures + assumptions + citations |
| `aaa_manage_adr` | `aaa_adr_tool.py` | Create / revise / supersede Architecture Decision Records |
| `aaa_manage_artifacts` | `aaa_artifacts_tool.py` | CRUD for requirements, assumptions, and clarification questions |
| `aaa_create_diagram_set` | `aaa_diagram_tool.py` | Persist diagram bundles |
| `aaa_record_validation_results` | `aaa_validation_tool.py` | Persist validation findings (WAF, security, etc.) |
| `aaa_record_iac_artifacts` | `aaa_iac_tool.py` | Persist IaC file artifacts |
| `aaa_generate_cost` | `aaa_cost_tool.py` | Persist cost estimate artifacts |
| `aaa_export_state` | `aaa_export_tool.py` | Export with traceability links |

### State update merge semantics

The state-update parser in `state_update_parser.py` uses a no-overwrite merge by default (existing fields are preserved unless explicitly replaced).  Two special flags alter this behavior:

- **`_replace_<key>: true`** — replaces the entire list for `<key>` instead of merging item-by-item.
- **`_remove: true`** on an individual item — removes the matching item (by `id`) from the existing list.

These flags are emitted by `aaa_manage_artifacts` when the action is `replace_all` or `remove`, respectively.

## Extending the agent system

- Add tools in `backend/app/agents_system/tools/`.
- Wire tool usage in the agent runner and update prompts if needed.
- Ensure MCP config is present in `backend/config/mcp/mcp_config.json`.

## Extending diagrams

- Add new diagram types in `backend/app/models/diagram/diagram.py`.
- Update the generator in `backend/app/services/diagram/`.
- Update UI labels in `frontend/src/components/diagrams/DiagramSetViewer.tsx`.
