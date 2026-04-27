# Documentation Home

This repository uses a domain-first documentation structure with a strict audience split.

## Audience Lanes

- **Agent lane (default for AI agents)**: `/docs/agents`
- **Human lane (comprehensive)**: domain folders under `/docs`

Agents should use `/docs/agents` as primary context and should not rely on human-comprehensive docs by default.

## Governance

- Documentation policy and update rules: [`/docs/operations/DOCUMENTATION_GOVERNANCE.md`](./operations/DOCUMENTATION_GOVERNANCE.md)
- Migration tracker and move/archive status: [`/docs/operations/DOC_MIGRATION_INDEX.md`](./operations/DOC_MIGRATION_INDEX.md)
- Policy ownership and precedence: [`/docs/operations/SOURCE_OF_TRUTH_MATRIX.md`](./operations/SOURCE_OF_TRUTH_MATRIX.md)
- Workflow and traceability policy: [`/docs/operations/WORKFLOW_TRACEABILITY_RUNBOOK.md`](./operations/WORKFLOW_TRACEABILITY_RUNBOOK.md)
- Agent/prompt/skill registry: [`/docs/operations/ACTIVE_ASSET_REGISTRY.md`](./operations/ACTIVE_ASSET_REGISTRY.md)
- CI check matrix and strictness policy: [`/docs/operations/CI_QUALITY_GATES.md`](./operations/CI_QUALITY_GATES.md)

## Domain Index (Human Lane)

### Architecture

- [`architecture/README.md`](./architecture/README.md)
- [`architecture/project-overview.md`](./architecture/project-overview.md)
- [`architecture/system-architecture.md`](./architecture/system-architecture.md)
- [`architecture/multi-agent-architecture.md`](./architecture/multi-agent-architecture.md)
- [`architecture/ADR-parallel-work-architecture.md`](./architecture/ADR-parallel-work-architecture.md) — Accepted decision record for the parallel-work architecture foundation
- [`architecture/LANE_OWNERSHIP.md`](./architecture/LANE_OWNERSHIP.md) — Logical lane ownership mapped to current backend and frontend folders
- [`architecture/PROJECTSTATE_DECOMPOSITION_INVENTORY.md`](./architecture/PROJECTSTATE_DECOMPOSITION_INVENTORY.md) — Observed ProjectState blob key inventory from the local projects database
- [`architecture/ARCHITECTURE_ENFORCEMENT_CI.md`](./architecture/ARCHITECTURE_ENFORCEMENT_CI.md) — Import-linter, freeze policy, and ESLint boundary checks
- [`architecture/FEATURE_DEVELOPMENT_GUIDE.md`](./architecture/FEATURE_DEVELOPMENT_GUIDE.md) — How to add a feature, workspace tab, contract, or agent-tool registration under the new architecture
- [`architecture/codebase-architecture.excalidraw`](./architecture/codebase-architecture.excalidraw)
- [`architecture/arch_mindmap.json`](./architecture/arch_mindmap.json)
- [`architecture/PARALLEL_WORK_ARCHITECTURE_IMPLEMENTATION.md`](./architecture/PARALLEL_WORK_ARCHITECTURE_IMPLEMENTATION.md) — Detailed implementation plan for monorepo parallel-work restructuring (5 phases), including the completed shared/feature migration, legacy backend root removal (`core`, `routers`, `services`), and blocking architecture CI gates

### Backend

- [`backend/README.md`](./backend/README.md)
- [`backend/BACKEND_REFERENCE.md`](./backend/BACKEND_REFERENCE.md) — Backend entry points, API surface, current ProjectState decomposition status, eval/E2E harness locations, the canonical pending-changes v1 API surface (`/pending-changes` with hidden `/changes` compatibility aliases; `revise` disabled), the project-notes + quality-gate + trace workspace endpoints, the typed project-chat `workflow_result` + canonical SSE event contract, and the SQLite-backed LangGraph thread-memory persistence path
- [`backend/AI_PROVIDER_ROUTING.md`](./backend/AI_PROVIDER_ROUTING.md)
- [`backend/AZURE_FOUNDRY_SETUP.md`](./backend/AZURE_FOUNDRY_SETUP.md)
- [`backend/COPILOT_SETUP.md`](./backend/COPILOT_SETUP.md)
- [`backend/DATA_ROOT_STORAGE_POLICY.md`](./backend/DATA_ROOT_STORAGE_POLICY.md)
- [`backend/TESTING_DEPENDENCY_INJECTION.md`](./backend/TESTING_DEPENDENCY_INJECTION.md)
- [`backend/EVAL_HARNESS.md`](./backend/EVAL_HARNESS.md) — Phase 0 golden-scenario eval harness for committed normalized runner reports
- [`../backend/config/prompts/README.md`](../backend/config/prompts/README.md) — Prompt stack layer architecture, architect_briefing.yaml contract, and modular composition order (P1/P2/P13)

### Refactor

- [`refactor/plan-functional-overhaul.md`](./refactor/plan-functional-overhaul.md) — **Active** master plan for the AAA functional overhaul (prompt, tools, UX, memory, observability). Supersedes AAA-refactor.md.
- [`refactor/AAA-refactor.md`](./refactor/AAA-refactor.md) — Superseded by `plan-functional-overhaul.md`. Kept for historical reference.
- [`refactor/plan-ai-foundry-migration.md`](./refactor/plan-ai-foundry-migration.md) — Completed Azure OpenAI to Azure AI Foundry provider migration plan and execution record

### Ingestion

- [`ingestion/IMPLEMENTATION_PLAN.md`](./ingestion/IMPLEMENTATION_PLAN.md)
- [`ingestion/review-ingestion-codebase-20260208.md`](./ingestion/review-ingestion-codebase-20260208.md)

### Frontend

- [`frontend/README.md`](./frontend/README.md)
- [`frontend/FRONTEND_REFERENCE.md`](./frontend/FRONTEND_REFERENCE.md) — Frontend structure, unified workspace tabs (including notes, quality gate, and trace), and project-chat SSE parsing notes for typed `workflowResult` payloads and canonical stream-event handling
- [`frontend/UX_IDE_WORKFLOW.md`](./frontend/UX_IDE_WORKFLOW.md)
- [`frontend/UNIFIED_UX_IMPLEMENTATION_CHECKLIST.md`](./frontend/UNIFIED_UX_IMPLEMENTATION_CHECKLIST.md)

### Operations

- [`operations/README.md`](./operations/README.md)
- [`operations/history/README.md`](./operations/history/README.md)
- [`operations/DEVELOPMENT_GUIDE.md`](./operations/DEVELOPMENT_GUIDE.md)
- [`waf_normalization_implementation/README.md`](./waf_normalization_implementation/README.md)

### Agent Enhancement

- [`Agent_Enhancement/PROJECT_MEMORY_CONTEXT_IMPLEMENTATION_BREAKDOWN.md`](./Agent_Enhancement/PROJECT_MEMORY_CONTEXT_IMPLEMENTATION_BREAKDOWN.md) — Memory & context engineering plan (4 phases, all complete)
- [`Agent_Enhancement/ASSISTANT_QUALITY_IMPROVEMENT_TASK_PLAN.md`](./Agent_Enhancement/ASSISTANT_QUALITY_IMPROVEMENT_TASK_PLAN.md) — Quality improvement task plan (Wave 1 complete). **P6 (Generate Architect Briefing from Pending Changes)** is now implemented: `PendingChangeBriefingService` generates stage-aware briefings (`propose_candidate`, `pricing`, `iac`, `validate`, `clarify`) injected into the agent response when the LLM output is a thin receipt. **P12 (Typed Contracts for Deterministic Stage Outputs)** is now implemented: 5 Pydantic output contracts (`RequirementsExtractionOutput`, `ClarificationPlanOutput`, `ArchitectureDraftOutput`, `ValidationOutput`, `AdrDraftOutput`) plus a `_parse_and_validate_output` helper in `backend/app/agents_system/contracts/stage_contracts.py`; the validate node uses these contracts for typed findings introspection with graceful fallback on malformed output.

## Agent Lane Index

- [`agents/README.md`](./agents/README.md)
- [`agents/AGENT_DOC_TEMPLATE.md`](./agents/AGENT_DOC_TEMPLATE.md)
- [`agents/project-overview.agent.md`](./agents/project-overview.agent.md)
- [`agents/system-architecture.agent.md`](./agents/system-architecture.agent.md)
- [`agents/multi-agent-architecture.agent.md`](./agents/multi-agent-architecture.agent.md)
- [`agents/data-root-storage.agent.md`](./agents/data-root-storage.agent.md)

## Historical / In-Progress Material

These files are currently in migration and may be archived or split:

- Implementation completion summaries
- Legacy migration plans
- Review and analysis dumps
- Historical phase/spec artifacts (moved to operations history)

See the live status table in [`operations/DOC_MIGRATION_INDEX.md`](./operations/DOC_MIGRATION_INDEX.md).

Primary history buckets:

- [`operations/history/implementation-history/`](./operations/history/implementation-history/)
- [`operations/history/plans-and-phases/`](./operations/history/plans-and-phases/)
- [`operations/history/reviews/`](./operations/history/reviews/)
- [`operations/history/analysis/`](./operations/history/analysis/)

## Compatibility Pointers (Legacy Paths)

Temporary root-level pointer files are kept for backward compatibility during migration.

Canonical references should use domain and history paths listed above.

Current legacy pointers are tracked in [`operations/DOC_MIGRATION_INDEX.md`](./operations/DOC_MIGRATION_INDEX.md).

## Allowed Documentation Exceptions (outside `/docs`)

These technical READMEs are intentionally local to code and must stay discoverable from this index:

- [`/backend/app/agents_system/langgraph/README.md`](../backend/app/agents_system/langgraph/README.md) — Code-near LangGraph runtime guide, including SQLite-backed thread-memory persistence details
- [`/backend/app/kb/README.md`](../backend/app/kb/README.md)

Add new exceptions only when code-near maintainability clearly benefits.

---

**Status**: Active  
**Last Updated**: 2026-04-17
**Owner**: Engineering

