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
- ADR lifecycle mutations now have a deterministic backend service in `backend/app/features/agent/application/adr_lifecycle_service.py`; later stage workers can call it to normalize ADR payloads and preserve traceability during draft/accepted/rejected/superseded transitions.
- Validate-stage turns now branch into `backend/app/agents_system/langgraph/nodes/validate.py`, which runs the deterministic WAF evaluator, feeds actionable gaps into `backend/app/agents_system/services/waf_findings_worker.py`, and emits validation-tool-compatible checklist deltas through the existing persistence/update path; it deterministically skips when checklist/evidence input is insufficient.

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
