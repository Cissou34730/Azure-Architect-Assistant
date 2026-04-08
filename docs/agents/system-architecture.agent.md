# System Architecture (Agent)

## Purpose

Concise architecture reference for agents performing coding and documentation tasks.

## Current State

- Runtime topology: frontend (React/Vite) -> backend (FastAPI) -> external AI/knowledge services.
- Backend ownership:
  - canonical feature APIs in `backend/app/features/*`
  - shared runtime code in `backend/app/shared/*`
  - orchestration/platform in `backend/app/agents_system`
  - legacy compatibility and not-yet-migrated surfaces still exist in `backend/app/{routers,services,core}`
- Frontend ownership:
  - shell and route registry in `frontend/src/app`
  - feature-local UI/hooks/api/types in `frontend/src/features/*`
  - reusable UI/hooks/http/config/lib in `frontend/src/shared/*`
- Startup lifecycle initializes DBs and key services; KB index loading is lazy.
- Persistent storage includes project, ingestion, and diagram SQLite databases plus file-based KB indices.
- Project state reads are composed: architecture inputs live in `project_architecture_inputs`, stable artifact families live in `project_state_components`, and `/api/projects/{project_id}/workspace` is the canonical read surface.
- Approval-first runtime behavior is active for requirements extraction: when project chat routes to `extract_requirements`, the LangGraph workflow short-circuits into a dedicated stage worker, records a pending requirements bundle, and skips the generic LLM/postprocess path before any canonical `requirements` mutation.
- Clarify-stage turns can also short-circuit into a dedicated planner worker that groups 3-5 high-impact questions from canonical requirements, ambiguity markers, WAF gaps, mindmap gaps, and prior clarification history instead of relying on the generic agent path.
- When open clarification questions already exist, clarify-stage turns now short-circuit into a dedicated clarification-resolution worker that converts the user's answers into approval-first pending change sets (updated requirements, answered questions, and new assumptions) instead of mutating canonical state directly.
- `propose_candidate` still reuses `backend/app/agents_system/langgraph/nodes/architecture_planner.py`, but that planner now acts as the explicit synthesizer seam and emits `architecture_synthesis_execution_artifact` metadata so evaluation/review flows can verify evidence-packet, WAF, and mindmap-delta coverage requirements.
- ADR runtime is now approval-first as well: `backend/app/agents_system/langgraph/nodes/manage_adr.py` short-circuits ADR turns into a dedicated stage worker, `backend/app/agents_system/services/adr_drafter_worker.py` enforces a structured LLM drafting seam, and `backend/app/features/projects/application/pending_changes_merge_service.py` only applies ADR create/supersede commands through `backend/app/features/agent/application/adr_lifecycle_service.py` during approval.
- Validate-stage turns now branch into `backend/app/agents_system/langgraph/nodes/validate.py`, which runs the deterministic WAF evaluator, feeds actionable gaps into `backend/app/agents_system/services/waf_findings_worker.py`, and emits validation-tool-compatible checklist deltas through the existing persistence/update path; it deterministically skips when checklist/evidence input is insufficient.
- Pricing-stage turns now branch into `backend/app/agents_system/langgraph/nodes/cost_estimator.py`, whose dedicated cost-stage worker reuses `prepare_cost_estimator_handoff`, the specialized cost estimator node, and `aaa_record_cost_estimate` so spend-focused turns avoid the generic agent loop while keeping normal postprocess/apply persistence.
- IaC-stage turns now branch into `backend/app/agents_system/langgraph/nodes/iac_generator.py`, whose dedicated stage worker reuses `prepare_iac_generator_handoff`, the specialized IaC generator node, and `aaa_record_iac_artifacts` so Terraform/Bicep requests avoid the generic agent loop while keeping normal postprocess/apply persistence.
- The E2E regression harness now treats `generate_iac` separately from pricing/export: `scripts/e2e/aaa_e2e_runner.py` records dedicated `iacPayload` summaries from persisted `iacArtifacts`, and `backend/tests/eval/reporting.py` flags missing IaC files or validation evidence as eval regressions.
- The same E2E harness now records dedicated `clarifyPayload`, `candidatePayload`, and `adrPayload` summaries so grouped clarification questions, persisted candidate payloads, and ADR pending change sets each fail with stage-specific eval diagnostics. `architecture_synthesis_execution_artifact` is not yet surfaced through project-chat responses, so candidate synthesis-artifact evals remain blocked on that runtime signal.
- Context assembly is budget-aware: `backend/app/agents_system/config/prompt_loader.py` truncates composed orchestrator directives when a positive context budget is supplied, `backend/app/agents_system/langgraph/nodes/context.py` uses `aaa_context_max_budget_tokens` for context-pack assembly, and Phase 11 now enables the `aaa_thread_memory_enabled` checkpointer plus `aaa_context_compaction_enabled` by default.
- Conversation compaction templates are YAML-backed: `backend/app/agents_system/memory/compaction_service.py` now reads `backend/config/prompts/memory_compaction_prompt.yaml` through `PromptLoader` instead of carrying an inline duplicate prompt.

## Do / Don't

### Do

- Keep feature changes within layer boundaries.
- Prefer `features/*` and `shared/*` imports over legacy root folders.
- Update this document for architecture-level behavior changes.
- Use human docs only when deeper implementation detail is required by maintainers.

### Don't

- Mix detailed historical migration narratives into this file.
- Record transient implementation status updates here.

## Decision Summary

- Maintain a feature/shared architecture on both backend and frontend.
- Treat `agents_system` as platform/orchestration, not a feature package.
- Use `/api/projects/{project_id}/workspace` as the canonical composed state/workspace read; `/state` is compatibility-only.
- Keep this file as stable architecture snapshot, not project log.

## Update Triggers

Update this file when:

- runtime topology changes
- layering or module ownership changes
- persistence model changes materially

## Metadata

- Status: Active
- Last Updated: 2026-04-08
- Owner: Engineering
