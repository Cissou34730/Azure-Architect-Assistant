# Lane Ownership

This file maps the logical lanes from the parallel-work architecture plan onto the current repository layout. The lane model now drives both documentation and the repository `CODEOWNERS` map.

## Lane Map

| Lane | Responsibility | Current backend areas | Current frontend areas |
| --- | --- | --- | --- |
| Projects workspace | Project CRUD, decomposed state orchestration, document lifecycle, workspace shell composition | `backend/app/features/projects/api/`, `backend/app/features/projects/application/`, `backend/app/features/projects/contracts/`, `backend/app/features/projects/infrastructure/`, `backend/app/models/project.py` | `frontend/src/features/projects/` |
| Agent workflow | Chat orchestration, AAA tools, proposal generation, agent transport | `backend/app/features/agent/api/`, `backend/app/features/agent/application/`, `backend/app/features/agent/infrastructure/`, `backend/app/agents_system/` | `frontend/src/features/agent/` |
| Knowledge and ingestion | Knowledge base management, KB query, ingestion jobs, document processing pipelines | `backend/app/features/knowledge/`, `backend/app/features/ingestion/` | `frontend/src/features/knowledge/`, `frontend/src/features/ingestion/` |
| Diagrams and checklists | Diagram generation, WAF evaluation, architecture review artifacts | `backend/app/features/diagrams/`, `backend/app/features/checklists/` | `frontend/src/features/diagrams/`, checklist workspace contributors inside `frontend/src/features/projects/workspace/` |
| Platform and shared | Configuration, database access, AI providers, MCP clients, logging, app shell, common UI and utilities | `backend/app/shared/`, `backend/app/main.py`, `backend/app/lifecycle.py`, `backend/app/service_registry.py` | `frontend/src/app/`, `frontend/src/shared/` |

## Guidance

1. Use these lanes as the ownership boundary for feature work, reviews, and future folder moves.
2. Keep `agents_system` in the agent workflow lane, but continue to expose reusable contracts through feature or shared packages rather than cross-lane internals.
3. Treat the remaining top-level horizontal folders as platform surfaces or migration sources, not long-term homes for feature logic.
4. Update `.github/CODEOWNERS` whenever a lane gains or loses canonical folders.