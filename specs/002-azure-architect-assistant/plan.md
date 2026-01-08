# Implementation Plan: Azure Architect Assistant (AAA)

**Branch**: `002-azure-architect-assistant` | **Date**: 2026-01-08 | **Spec**: [specs/002-azure-architect-assistant/spec.md](specs/002-azure-architect-assistant/spec.md)
**Input**: Feature specification from `/specs/002-azure-architect-assistant/spec.md`

## Summary

Enhance the existing project/document/chat/diagram backend into a **document-driven Azure Architect Assistant** that:

- Ingests mixed-format project documents and extracts structured requirements
- Generates candidate Azure architectures with explicit assumptions
- Validates against WAF (all pillars) and security baselines with findings
- Records ADRs and full traceability across artifacts
- Generates IaC and cost estimates (P3)
- Uses `/docs/arch_mindmap.json` (13 topics) as the invariant coverage backbone
- Consults reference documents and Microsoft Learn MCP on every iteration, recording citations

The implementation is **integration-first**:

- **Initial phase** extends existing Project Management endpoints/services for project setup, document upload, and document analysis.
- **All discussion, iteration, and artifact generation** (candidates, ADRs, findings, IaC/cost narratives, citations) is executed via the existing **Agent System** (`backend/app/agents_system/`) using the project-aware agent endpoint and state update pipeline.

## Technical Context

**Language/Version**: Python 3.10+ (FastAPI async); TypeScript 5+ with React 19 and TailwindCSS 4.1; Vite
**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy async, aiosqlite; pytest; existing MCP client under `backend/app/services/mcp/`; existing Agent System under `backend/app/agents_system/`
**Storage**:
- Project DB: async SQLite at `backend/data/projects.db` via `backend/app/projects_database.py`
- Project artifacts/state: `ProjectState.state` JSON blob (`backend/app/models/project.py`)
**Testing**: pytest (`backend/tests/`), plus existing scripts
**Target Platform**: Local dev on Windows; deployment target is a Linux container
**Project Type**: Web application (separate `backend/` and `frontend/`)
**Performance Goals**: Meet spec success criteria (SC-004 ingestion parse success, SC-006 IaC validation, SC-011 citations, SC-001/SC-014 mind map coverage)
**Constraints**:
- Constitution: SRP, explicit naming, zero duplication, YAGNI, integration-first
- TailwindCSS-only styling
- No new frameworks without approval
**Scale/Scope**: Deliver the 7 user stories in spec.md; avoid additional UX/flows beyond spec

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] I. Single Responsibility - PASS (project_management handles project/doc lifecycle; agents_system handles architecture reasoning and state updates)
- [x] II. Automated Deployment - N/A (prototype/local dev; milestone-gated in constitution)
- [x] III. Explicit Naming - PASS (explicit module/service naming mandated)
- [x] IV. Zero Duplication - PASS (reuse existing project/doc/chat/diagram/MCP services)
- [x] V. YAGNI - PASS (persist AAA artifacts in existing ProjectState JSON; avoid premature DB tables)
- [x] VI. Integration First - PASS (extend existing endpoints and services; AAA folders are already present)
- [x] VII. Existing code discovery performed and documented - PASS (see Phase 0 outputs)
- [x] VIII. Instruction files compliance verified - PASS (`.github/copilot-instructions.md` + TS/Python instructions)

Violations: None.

## Project Structure

### Documentation (this feature)

```text
specs/002-azure-architect-assistant/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
└── app/
    ├── models/
    │   ├── project.py
    │   └── aaa/                  # exists (currently empty; avoid new tables early)
    ├── routers/
    │   ├── project_management/   # upload/analyze/state/chat/proposal endpoints
    │   ├── diagram_generation/
    │   ├── ingestion.py
    │   └── aaa/                  # exists (currently empty)
    ├── services/
    │   ├── diagram/
    │   ├── kb/
    │   ├── rag/
    │   ├── mcp/
    │   └── aaa/                  # exists (currently empty; do not build parallel orchestration)
    └── lifecycle.py              # initializes MCP client and diagram DB

backend/
└── app/
    └── agents_system/            # agent runner, prompts, tools, state update parsing (router at /api/agent)

frontend/
└── src/
    └── features/
        └── aaa/                  # exists (currently empty)

docs/
└── arch_mindmap.json
```

**Structure Decision**:

- Keep **Project** as the container (`/api/projects/*`), **Project documents** as input corpus, and **ProjectState JSON** as the canonical persisted architecture state.
- Extend `backend/app/routers/project_management/*` for the **initial ingestion + analysis** phase only (US1 foundation).
- Use `backend/app/agents_system/agents/router.py` (`/api/agent/projects/{project_id}/chat`) for:
  - all architecture discussion/iteration (US7)
  - all artifact generation that updates ProjectState (candidates, ADRs, findings, IaC/cost narratives)
  - citation logging (MCP + reference docs) attached to artifacts in ProjectState
- Avoid adding a parallel `/api/aaa/*` router unless a later phase proves it necessary.
- Reuse existing services:
  - MCP client: `backend/app/services/mcp/learn_mcp_client.py` (already initialized in `backend/app/lifecycle.py`)
  - Diagram generation: `backend/app/services/diagram/` and `backend/app/routers/diagram_generation/`
  - KB/RAG: `backend/app/services/kb/`, `backend/app/services/rag/`, and `backend/app/kb/`
  - Agent state pipeline: `backend/app/agents_system/services/state_update_parser.py` and `backend/app/agents_system/services/project_context.py`

## Complexity Tracking

None (no constitution violations).

## Vertical Slice Delivery (aligned to spec user stories)

Deliver end-to-end slices using existing project state and services.

- **US1 (P1)**: Document ingestion → normalized corpus → structured requirements + ambiguities → C4 L1 (extend project_management analyze-docs)
- **US2 (P1)**: Candidate architecture generation (≥1) + assumptions + updated diagrams + WAF baseline init (triggered via agents_system project chat; state updates persisted)
- **US7 (P1)**: Document-driven iteration with MCP/reference queries recorded and mind map topic prompting (agents_system)
- **US3 (P2)**: ADR CRUD + lifecycle + traceability links
- **US4 (P2)**: Validation runner → findings (severity/remediation) + WAF/security updates
- **US5 (P3)**: IaC generation + static checks + cost estimate with assumptions
- **US6 (P3)**: Mind map coverage tracking + end-to-end traceability export

## Phase 0: Research (output: research.md)

Focus: confirm reuse points, persistence strategy, and where to hook mind map/citation logging.

- Confirm existing endpoints: project upload/analyze/state/proposal in `backend/app/routers/project_management/`
- Confirm existing agent endpoints and state update pipeline in `backend/app/agents_system/agents/router.py`
- Confirm MCP client lifecycle and how to record queries/sources
- Confirm diagram service entrypoints and diagram persistence
- Confirm persistence strategy: extend `ProjectState.state` JSON with typed schemas

## Phase 1: Design Assets (outputs: data-model.md, contracts/, quickstart.md)

- Define ProjectState schema extensions for AAA artifacts (requirements, candidates, ADRs, findings, IaC, costs, mind map coverage)
- Document the existing endpoints used by AAA.
  - AAA “actions” are driven via the existing project-aware agent chat endpoint and persisted through ProjectState updates.
- Document a quickstart that uses existing project creation + document upload workflow

## Phase 2: Implementation Planning (output: tasks.md)

Generate tasks grouped by user story, prioritizing:

1) US1 + US2 + US7 (MVP: document-driven candidate architecture with citations)
2) US3 + US4 (governance + validation)
3) US5 + US6 (IaC + costs + exports)

