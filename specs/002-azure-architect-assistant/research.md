# Research: Azure Architect Assistant (AAA)

This document resolves planning unknowns and captures decisions needed to keep implementation **accurate**, **minimal**, and **integration-first**.

## Key Discoveries (Existing Code)

### Existing Project Workflow (Backend)

- Project/document endpoints live under `backend/app/routers/project_management/` and are mounted at `/api`.
- Document ingestion already exists via `POST /api/projects/{project_id}/documents`.
- Document analysis already exists via `POST /api/projects/{project_id}/analyze-docs` and persists output in `ProjectState`.
- Candidate architecture proposal already exists via `GET /api/projects/{project_id}/architecture/proposal` (SSE).

### Existing Services to Reuse

- MCP: `backend/app/services/mcp/learn_mcp_client.py` is initialized in `backend/app/lifecycle.py`.
- Diagram: `backend/app/services/diagram/` and `backend/app/routers/diagram_generation/`.
- KB/RAG: `backend/app/services/kb/`, `backend/app/services/rag/`, and `backend/app/kb/`.

### Storage Baseline

- Projects DB is async SQLite via `backend/app/projects_database.py` storing:
  - `Project` (includes `text_requirements`)
  - `ProjectDocument` (includes `raw_text`)
  - `ProjectState` (JSON blob) as the primary evolving architecture state

## Decisions

### Decision 1: Persist AAA artifacts in `ProjectState.state` JSON

- **Decision**: Extend the existing `ProjectState.state` JSON schema to store AAA artifacts (requirements, ADRs, WAF, findings, IaC, cost, mind map coverage, citations).
- **Rationale**:
  - Minimizes DB schema churn and migrations (YAGNI)
  - Aligns with existing code pattern: analyze-docs + chat already produce and persist `ProjectState`
  - Enables stable IDs and traceability without premature relational modeling
- **Alternatives considered**:
  - New SQL tables for each entity (Requirement/ADR/Finding/etc.) — rejected for now due to complexity and premature optimization.

### Decision 2: Extend existing project endpoints before adding new routers

- **Decision**: Extend `backend/app/routers/project_management/` for the **initial ingestion + analysis** phase only, and use `backend/app/agents_system/agents/router.py` (`/api/agent/projects/{project_id}/chat`) for all discussion and artifact generation that mutates ProjectState.
- **Rationale**:
  - Keeps workflow cohesive around an existing Project container
  - Avoids parallel competing APIs
- **Alternatives considered**:
  - A separate `/api/aaa/*` router — rejected for now to avoid parallel orchestration and duplication.

### Decision 3: Mind map is loaded as a validated dependency

- **Decision**: Treat `/docs/arch_mindmap.json` as required input, validate presence of all 13 top-level topics at initialization, and store coverage in ProjectState.
- **Rationale**:
  - Direct requirement in FR-019..FR-021 and SC-001/SC-013/SC-014
- **Alternatives considered**:
  - Hardcoded topic list — rejected (must be loaded from file).

### Decision 4: MCP + citations are first-class artifacts

- **Decision**: Record MCP queries (terms, result URLs, selected excerpts/summary) and attach citations to CandidateArchitectures, Findings, ADRs, and IaC artifacts.
- **Rationale**:
  - Required by FR-015..FR-018 and SC-011..SC-012
- **Alternatives considered**:
  - “Best-effort” citations only in chat — rejected; must be captured in persisted artifacts.

## Open Questions (Deferred — but tracked)

- Exact IaC target (Bicep only vs Bicep + Terraform) and which static validators to run in CI.
- Cost estimation approach (pricing API vs documented assumptions) given environment constraints.
