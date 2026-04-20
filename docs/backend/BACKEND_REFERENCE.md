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
- `GET /api/projects/{project_id}/notes` - list persisted long-term project notes (`decision`, `context`, `question`, `risk`) for the unified workspace notes tab
- `POST /api/projects/{project_id}/notes` - create a persisted project note
- `PUT /api/projects/{project_id}/notes/{note_id}` - update an existing project note
- `DELETE /api/projects/{project_id}/notes/{note_id}` - delete a persisted project note
- `GET /api/projects/{project_id}/quality-gate` - compute the current quality gate report from canonical project state plus persisted `project_trace_events`, including weighted WAF coverage, mindmap coverage, open clarifications, missing deliverables, and a recent trace-activity summary for the unified workspace quality tab
- `GET /api/projects/{project_id}/trace` - list persisted `project_trace_events` for the project (optionally filtered by `thread_id` and bounded by `limit`) for the unified workspace trace tab timeline
- `GET /api/projects/{project_id}/messages`
- `GET /api/projects/{project_id}/pending-changes` - canonical pending change-set summary route backed by dedicated `pending_change_sets` / `artifact_drafts` tables and projected into `projectState.pendingChangeSets`; supports an optional `status` filter. Legacy `GET /api/projects/{project_id}/changes` remains as a hidden compatibility alias.
- `GET /api/projects/{project_id}/pending-changes/{change_set_id}` - canonical pending change-set detail route, including artifact drafts and proposed patch payload loaded from dedicated pending-change tables. Legacy `GET /api/projects/{project_id}/changes/{change_set_id}` remains as a hidden compatibility alias.
- `POST /api/projects/{project_id}/pending-changes/{change_set_id}/approve` - canonical approval route; merges `proposedPatch` into canonical project state and returns the reviewed change set plus updated state. Legacy `POST /api/projects/{project_id}/changes/{change_set_id}/approve` remains as a hidden compatibility alias.
- `POST /api/projects/{project_id}/pending-changes/{change_set_id}/reject` - canonical rejection route; marks a pending change set rejected without mutating canonical project state. Legacy `POST /api/projects/{project_id}/changes/{change_set_id}/reject` remains as a hidden compatibility alias.
- `POST /api/projects/{project_id}/changes/{change_set_id}/revise` - disabled compatibility endpoint that now returns `410 Gone` because revise/supersession is deferred to v2.
- `POST /api/projects/{project_id}/extract-requirements` - loads parsed project documents, runs the Phase 4 extraction worker, and records a pending requirements change set for review.
- `GET /api/projects/{project_id}/architecture/proposal` (SSE)

### Settings
- `GET /api/settings/architect-profile` - read the single-user architect profile persisted for installation-wide defaults
- `PUT /api/settings/architect-profile` - update the persisted architect profile
- `GET /api/settings/llm-options`
- `PUT /api/settings/llm-selection`
- `GET /api/settings/copilot/status`
- `POST /api/settings/copilot/login`
- `POST /api/settings/copilot/logout`

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
- `POST /api/agent/projects/{project_id}/chat/stream` - SSE stream whose `final` event preserves the legacy top-level response fields and now includes a typed `workflow_result` object (`stage`, `nextStep`, `toolCalls`, `citations`, `structuredPayload`) for structured chat interactions; the stream also emits canonical `stage`, `text`, and `tool_call` events while keeping legacy `token` / `tool_start` compatibility frames.
- `GET /api/agent/projects/{project_id}/history`
- `GET /api/agent/health`
- `GET /api/agent/capabilities`

### Diagram generation
- `POST /api/diagram-sets`
- `GET /api/diagram-sets/{diagram_set_id}`

## Data models (high level)

- Project: name, requirements, created/updated timestamps.
- Project state: mixed compatibility blob + composed reads. Architecture inputs live in `project_architecture_inputs`, most remaining top-level artifact families live in `project_state_components`, pending review bundles now live in dedicated `pending_change_sets` and `artifact_drafts` tables, normalized checklist rows are the preferred source for `wafChecklist`, and composed reads still project `pendingChangeSets` back into the compatibility payload for existing callers.
- Architect profile: installation-scoped singleton row in `architect_profiles`, storing default region, IaC flavor, compliance posture, cost ceiling, VM preferences, DevOps maturity, and free-form notes.
- Project notes: normalized `project_notes` rows linked to `projects.id`, used by the unified workspace notes tab for durable long-term notes.
- Quality gate report: computed on demand by `app.features.projects.application.quality_gate_service.QualityGateService` from the canonical composed project state plus persisted `project_trace_events`; no additional persistence layer or migration is required.
- Project trace timeline: read on demand by `app.features.projects.application.trace_service.ProjectTraceService`, which projects normalized `project_trace_events` rows into the `/trace` workspace timeline contract without introducing a second trace store.
- Knowledge base: config in `data/knowledge_bases/config.json` with per-KB settings.
- Diagram set: input description, diagrams, ambiguities, stored in `data/diagrams.db`.

## ProjectState decomposition status

- Dedicated architecture-input persistence now lives in `backend/app/models/project.py` as `ProjectArchitectureInputs` (`project_architecture_inputs` table).
- Dedicated generic artifact persistence now lives in `backend/app/models/project.py` as `ProjectStateComponent` (`project_state_components` table), keyed by `project_id + component_key`.
- Canonical read path: `app.agents_system.services.project_context.read_project_state(...)` composes the compatibility blob with `project_architecture_inputs`, `project_state_components`, dedicated pending-change tables, and normalized checklist rows, then applies AAA normalization and document-derived metadata.
- Deterministic Phase 8 checklist evaluation now lives in `app.agents_system.services.waf_evaluator.WAFEvaluatorService`, which inspects recomposed project state and emits structured WAF coverage summaries for the dedicated validate-stage graph worker.
- The follow-on validate-stage findings worker now lives in `app.agents_system.services.waf_findings_worker.WAFFindingsWorker`; it turns actionable evaluator items into validation-tool-ready `findings` + `wafEvaluations` payloads, preserves stable finding ids for checklist linking, backfills source citations from recorded `referenceDocuments` / `mcpQueries` when needed, and now feeds the dedicated validate-stage runtime path.
- Clarification-answer turns now branch through `app.features.agent.application.clarification_resolution_worker.ClarificationResolutionWorker`, which packages resolved requirement updates, answered clarification-question statuses, and new assumptions into `_clarificationResolution` pending-change bundles; `app.features.projects.application.pending_changes_merge_service.PendingChangesMergeService` applies that command only during approval.
- The `propose_candidate` architecture synthesizer continues to reuse `app.agents_system.langgraph.nodes.architecture_planner`, but that node now carries an explicit synthesis output contract (single-candidate default, evidence-packet coverage, WAF/mindmap deltas, C4 requirements) and emits `architecture_synthesis_execution_artifact` metadata so review/eval flows can assert the planner stayed on the approval-first pending-change path.
- The E2E eval harness (`scripts/e2e/aaa_e2e_runner.py` + `backend/tests/eval/reporting.py`) now records dedicated `clarifyPayload`, `candidatePayload`, and `adrPayload` summaries so regressions in grouped clarification questions, persisted candidate payloads, and ADR pending-change bundles are surfaced separately from export/cost/IaC slices; synthesizer-artifact coverage remains blocked until `architecture_synthesis_execution_artifact` is exposed through project-chat responses.
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
- Residual exceptions: `ProjectState.state` can still hold unknown historical keys, legacy `pendingChangeSets` payloads for rows not yet rewritten through the new service path, and legacy `wafChecklist` payloads for projects that have not yet been normalized into checklist rows. Those cases are compatibility fallbacks, not the preferred canonical store.

## Configuration and settings

- `.env` (repo root) provides ports, API keys, and storage paths.
- `backend/app/shared/config/app_settings.py` is the canonical runtime configuration entry point (use `get_app_settings()`).
- `backend/app/core/app_settings.py` remains only as a backward-compatible import target for out-of-tree callers; in-repo app code, migrations, and scripts now import `backend/app/shared/config/app_settings.py` directly.
- Add or change env-backed settings in settings mixins under `backend/app/core/settings/`, then consume through `AppSettings`.
- Shared logging and projects-database session helpers now resolve directly from `app.shared.logging.app_logging` and `app.shared.db.projects_database`; the old `app.core.app_logging`, `app.core.container`, `app.core.db`, and `app.projects_database` shim modules were removed in the final backend hardening pass.
- `backend/config/ingestion.config.json` and `backend/config/kb_defaults.json` are file-backed defaults loaded by `IngestionSettingsMixin` into `AppSettings` (`ingestion_queue`, `kb_defaults`).
- `backend/config/mcp/mcp_config.json` is loaded through `AppSettings.get_mcp_server_config(...)`.
- Storage paths come through `AppSettings`; relative values from process env or `.env` resolve against `backend/`. The fallback data root is `backend/data`, which covers `projects.db`, `ingestion.db`, and the `knowledge_bases/` directory.
- `SettingsModelsService` validates `PUT /api/settings/llm-selection` against provider model listings, rejects the legacy `azure` provider id in favor of `foundry`, and persists the active selection to `runtime_ai_selection.json`.
- `ArchitectProfileService` persists the single-user architect profile in the projects SQLite database; both the legacy summary builder and context-pack path now inject `ARCHITECT_PREFERENCES` plus recent `PROJECT NOTES` into agent prompt context.
- `backend/config/prompts/*.yaml` and `backend/config/checklists/*.json` are content/resource files (not env settings) loaded by dedicated services. `PromptLoader.compose_prompt(agent_type, stage, context_budget)` now assembles modular prompt fragments (`base_persona`, agent-specific routing, stage-specific instructions, tool strategy, guardrails), skips `orchestrator_routing.yaml` when a dedicated stage prompt is available, and falls back to `agent_prompts.yaml` only when modular files are absent; direct stage-worker call sites now use `load_prompt_file(...)` so they do not inherit legacy monolithic sections by accident.
- Agent runtime is LangGraph-only (legacy LangChain ReAct backend paths were removed).
- AI provider routing for `openai`, `foundry`, and `copilot` is documented in `docs/backend/AI_PROVIDER_ROUTING.md`.

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
| **LLMService** | `app/services/llm_service.py` | Connection pooling to OpenAI/Foundry-backed runtimes | HTTP client reuse, rate limiting |
| **AIService** | `app/services/ai/ai_service.py` | Provider abstraction (OpenAI, Foundry, Copilot, Anthropic) | Model caching, connection pooling |
| **ModelCapabilityCache** | `app/shared/ai/model_capability_cache.py` | Process-scoped cache of unsupported API parameters per (provider, model) | Learns from runtime errors, proactively strips params |
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

- `langgraph/graph_factory.py` — Project chat graph assembly; stage routing resolves before context summary/context-pack construction so stage-specific compaction sees the routed stage, `extract_requirements` has a dedicated runtime node, `clarify` now routes through a dedicated planner/resolution stage worker, `manage_adr` now branches into a dedicated ADR stage worker, `propose_candidate` routes through a dedicated research-worker → architecture-planner synthesizer slice, `validate` now branches into a dedicated validate-stage worker before the generic agent path, `pricing` now branches into a dedicated cost-stage worker that reuses the existing handoff + estimator nodes, `iac` now branches into a dedicated IaC-stage worker that reuses the specialized handoff + generator nodes while preserving `aaa_record_iac_artifacts`, and `export` now routes into a dedicated export-stage worker that reuses the AAA export tool instead of the generic agent loop. When `AAA_THREAD_MEMORY_ENABLED` is on, the compiled graph now uses a SQLite-backed LangGraph `AsyncSqliteSaver` rooted at `DATA_ROOT/checkpoints.db` instead of in-memory checkpoints. Phase 12 removed the abandoned multi-agent specialist branch and the old runtime flags, so project chat now follows a single graph/runtime path.
- `langgraph/adapter.py` — Project-chat adapter; mints an effective `thread_id` when the caller omits one so SQLite-checkpointer-backed graphs always receive a valid `configurable.thread_id`, echoes that effective thread identifier in the streaming `final` payload, assembles a typed `workflow_result` contract (stage, stage classification, next step, tool traces, citations, structured payload) alongside the legacy `answer` / `project_state` fields, and now validates/emits canonical SSE payloads for `stage`, `text`, `tool_call`, `tool_result`, `pending_change`, and `final` without removing the current legacy aliases. The `stage` event and `workflow_result.stageClassification` now carry the routed stage plus confidence/source/rationale metadata for downstream UX and eval consumers.
- `config/prompt_loader.py` — YAML prompt loader; supports both the legacy `agent_prompts.yaml` surface and modular prompt composition for stage-aware orchestrator prompts, exposes `load_prompt_file(...)` for file-only stage worker prompts, and truncates composed directives to the supplied context budget when one is provided.
- `memory/compaction_service.py` — Conversation compaction helper; loads `memory_compaction_prompt.yaml` through `PromptLoader` so both the system prompt and summary/update templates stay hot-reloadable in YAML.
- `memory/context_packs/stage_packers.py` — Stage-specific compaction builders; ADR packs read canonical `adrs`, validation packs summarize `wafChecklist.items[*].evaluations[*].status` from the current checklist payload, the context-pack runtime consumes `aaa_context_max_budget_tokens` as the pack assembly budget instead of reusing the compaction trigger threshold, and Phase 11 turns `aaa_context_compaction_enabled` / `aaa_thread_memory_enabled` on by default.
- `nodes/stage_routing.py` — Core stage enum, classification, retry logic. Classification now returns a typed stage-classification payload (`stage`, `confidence`, `source`, `rationale`) in addition to `next_stage`; rule guards now keep architecture-design language on `propose_candidate`, keep review-style ADR/code-review wording on `general`, keep IaC routing tied to Terraform/Bicep/IaC-specific wording, and still fall back to state-gap routing when intent rules do not match.
- `features/agent/infrastructure/tools/aaa_export_tool.py` — Canonical AAA export serializer; export payloads now include a `mindmapCoverageScorecard` with 13-topic evidence packaging built from current project artifacts.
- `nodes/agent_native.py` — Native LangGraph orchestrator node; builds system directives from the composed stage-aware prompt surface.
- `features/projects/application/pending_changes_service.py` — Read-side projection for `pendingChangeSets`, providing typed summaries/details without changing persistence semantics yet.
- `features/projects/application/pending_changes_merge_service.py` — Deterministic approval merge helper built on the existing non-overwrite state merge behavior; conflicts surface as 409s instead of silently overwriting canonical state, and explicit `_adrLifecycle` commands are executed through `ADRLifecycleService` only during approval.
- `features/projects/api/changes_router.py` — Canonical `/pending-changes` project-scoped pending change-set read/review endpoints plus hidden `/changes` compatibility aliases.
- `features/projects/application/quality_gate_service.py` + `features/projects/api/quality_gate_router.py` — Compute and expose the project-scoped quality gate report (`/quality-gate`) from canonical project state, normalized WAF/mindmap coverage inputs, and persisted trace-event summaries.
- `features/agent/contracts/extract_requirements.py` — Strict contracts for source-grounded extracted requirements, ambiguity markers, and bundle summaries.
- `features/agent/application/adr_lifecycle_service.py` — Deterministic ADR lifecycle helper for draft/create, reject, accept, and supersede transitions; normalizes ADR payloads and refreshes traceability links so later stage workers can mutate `projectState.adrs` without router-specific logic.
- `features/agent/application/clarification_planner_worker.py` — Clarify-stage worker that turns canonical requirements, ambiguity markers, WAF gaps, mindmap gaps, and prior clarification history into grouped high-impact question sets without mutating canonical state.
- `features/agent/application/requirements_extraction_service.py` — Exact-match requirement dedupe/bundling helper that preserves all document sources and rolls ambiguity notes forward.
- `features/agent/application/requirements_extraction_worker.py` — First Phase 4 worker path; formats parsed project documents for analysis, normalizes extracted requirements, builds a pending change set, and records it through the pending-change service.
- `features/agent/application/adr_management_worker.py` — Dedicated `manage_adr` worker that drafts ADR bundles (including supersession bundles) and records them as reviewable pending change sets before approval-time lifecycle application.
- `agents_system/services/adr_drafter_worker.py` — LLM-facing structured ADR drafting helper that enforces JSON output contracts for create/supersede actions before the management worker packages reviewable change sets.
- `agents_system/services/waf_findings_worker.py` — Phase 8 validation worker helper; packages actionable WAF evaluator gaps into remediation-focused findings plus linked checklist deltas for the dedicated validate-stage runtime.
- `features/projects/application/requirements_extraction_entry_service.py` — Project-scoped DB/document-loading entry point for requirements extraction; feeds parsed documents to the worker and returns the recorded pending change set.
- `nodes/routing/` — Per-agent routing subpackage (architecture_planner, iac_generator, saas_advisor, cost_estimator, `_helpers.py` for shared utils).
- `nodes/extract_requirements.py` — Dedicated Phase 4 stage worker; executes the requirements extraction entry service inside the graph, records a pending requirements bundle, refreshes project state, and emits a review-focused response without invoking the general LLM path.
- `nodes/manage_adr.py` — Dedicated Phase 7 stage worker; runs the ADR management worker inside the graph, records pending ADR/supersession bundles, refreshes project state, and skips the generic agent/postprocess mutation path for ADR turns.
- `nodes/research.py` — Phase 6 research-planning/runtime helper; turns research plans into grounded evidence packets (with consulted sources + evidence excerpts) and records a deterministic execution artifact before architecture synthesis.
- `nodes/validate.py` — Dedicated Phase 8 validate-stage worker; evaluates current architecture evidence with the deterministic WAF evaluator, invokes the WAF findings worker for actionable gaps, emits `aaa_record_validation_results`-compatible output, and deterministically skips when checklist/evidence input is insufficient.
- `nodes/iac_generator.py` — Dedicated Phase 10 IaC-stage worker; prepares IaC-specific handoff context, invokes the specialized IaC generator node, and surfaces explicit errors instead of falling back to the generic graph agent loop.
- `nodes/cost_estimator.py` — Dedicated Phase 9 cost-stage worker/runtime; prepares cost handoff context with the existing routing helper, executes the specialized cost estimator node, and records `costEstimates` for review-first persistence.
- `nodes/architecture_planner.py` — Dedicated architecture synthesizer for `propose_candidate`; consumes the research-worker handoff packets alongside requirements/NFR context and now receives grounded evidence excerpts/URLs instead of plan-only placeholders.
- `nodes/agent.py` — Main agent node entry (`run_agent_node`) for non-`extract_requirements` stage execution and guardrail shortcuts.
- `nodes/scope_guard.py` — Scope-detection patterns and guardrails.
- `nodes/waf_shortcuts.py` — Deterministic WAF-checklist shortcut handlers.
- `services/waf_evaluator.py` — Deterministic Phase 8 evaluator; scans recomposed architecture evidence (including ADRs and reference documents) and returns worker-friendly per-item WAF coverage with summary counts.
- `services/diagram/project_diagram_helpers.py` — Diagram business logic extracted from project_router.
- `services/project/document_normalization.py` — Requirements/questions normalization helpers.

## Evaluation and E2E harness

- `scripts/e2e/aaa_e2e_runner.py` — Canonical end-to-end AAA scenario runner; replays scenario chat turns against the agent API, records advisory/tool usage signals, captures dedicated cost-stage pricing logs plus persisted `costEstimates` summaries, records separate IaC artifact summaries from persisted `iacArtifacts`, and manages normalized goldens under `scripts/e2e/goldens/`.
- `scripts/e2e/scenarios/` — Golden scenario inputs used to baseline AAA behavior across requirements, architecture, ADR, validation, IaC, cost, and traceability flows.
- `backend/tests/eval/reporting.py` — Typed Phase 0 evaluation summary layer that converts the existing E2E runner report shape into rubric-friendly scenario/turn summaries for regression tracking, including export-payload, cost-payload, and IaC-payload regression checks.
- `backend/tests/eval/eval_runner.py` + `backend/tests/eval/golden_scenarios/` — Report-driven baseline harness for committed normalized eval snapshots; loads the representative scenario set, reuses `reporting.py` for scoring, and asserts expected baseline failures without re-implementing the live replay runner.

## AAA ProjectState tools

AAA tools still originate from `create_aaa_tools()` in `aaa_candidate_tool.py`, but project-state mutation now flows through `backend/app/agents_system/tools/tool_registry.py`. The registry narrows pending-change tools by stage, `tool_wrappers.py` upgrades legacy `AAA_STATE_UPDATE` tool responses into canonical typed confirmations, and those confirmations are recorded via the DB-backed `pending_change_sets` / `artifact_drafts` tables before postprocess runs. `postprocess.py` now treats canonical tool results as authoritative and only falls back to legacy text extraction for non-migrated paths.

The same registry also stage-scopes non-persistence runtime tools where v1 needs them: `azure_retail_prices` is exposed for general/pricing turns, `aaa_validate_mermaid_diagram` is exposed for general/candidate/validate turns, and `aaa_validate_iac_bundle` is exposed for general/IaC turns. The unified research facade remains an internal backend seam used by the research worker to materialize grounded packet contracts consistently.

| Tool | File | Purpose |
|------|------|---------|
| `aaa_generate_candidate_architecture` | `aaa_candidate_tool.py` | Persist candidate architectures + assumptions + citations |
| `aaa_manage_adr` | `aaa_adr_tool.py` | Create / revise / supersede Architecture Decision Records |
| `aaa_manage_artifacts` | `aaa_artifacts_tool.py` | CRUD for requirements, assumptions, and clarification questions |
| `aaa_create_diagram_set` | `aaa_diagram_tool.py` | Persist diagram bundles |
| `aaa_record_validation_results` | `aaa_validation_tool.py` | Persist validation findings (WAF, security, etc.) |
| `aaa_validate_mermaid_diagram` | `aaa_mermaid_validation_tool.py` | Validate Mermaid syntax with line-aware diagnostics |
| `aaa_validate_iac_bundle` | `aaa_iac_validation_tool.py` | Validate ARM/JSON/YAML plus lightweight Bicep/Terraform structure |
| `aaa_record_iac_artifacts` | `aaa_iac_tool.py` | Persist IaC file artifacts |
| `azure_retail_prices` | `azure_retail_prices_tool.py` | Query the public Azure Retail Prices API (public/no-auth, cached, structured items) |
| `research_tool.py` | `research_tool.py` | Internal unified facade + typed grounded research packet contract for the research worker |
| `aaa_generate_cost` | `aaa_cost_tool.py` | Persist cost estimate artifacts using the standalone Retail Prices tool path |
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


