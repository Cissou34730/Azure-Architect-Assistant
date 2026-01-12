# Project Overview

Azure Architecture Assistant is a full-stack app that helps architects analyze project requirements, query Azure knowledge bases, and generate architecture guidance and diagrams.

## Core workflows

- Architecture projects: capture requirements, upload documents, analyze them into a structured state, chat to refine, and generate a proposal.
- Azure Architect Assistant (AAA): use project-aware agent chat to generate candidates, ADRs, findings, IaC/cost narratives, and traceability artifacts into `ProjectState`.
- Knowledge bases: create a KB, ingest sources into a vector index, and query across one or more KBs.
- Agent chat: a ReAct-style agent that searches Microsoft documentation via MCP and answers questions with citations.
- Diagram generation: generate Mermaid-based functional, C4 context, and C4 container diagrams from a text description.

## Feature areas and where to look

- Projects: `backend/app/routers/project_management/` and `frontend/src/features/projects/`.
- Azure Architect Assistant (AAA): `backend/app/agents_system/` and `frontend/src/features/aaa/`.
- KB ingestion: `backend/app/ingestion/` and `frontend/src/components/ingestion/`.
- KB query: `backend/app/services/kb/` and `frontend/src/components/kb/`.
- Agent system: `backend/app/agents_system/` and `frontend/src/components/agent/`.
- Diagrams: `backend/app/services/diagram/` and `frontend/src/components/diagrams/`.

## Key components

- Backend: FastAPI service with modular routers for projects, KB management, ingestion, queries, agents, and diagram generation.
- Frontend: React + Vite UI with project workspace, KB management/query, agent chat, and diagrams.
- Storage: SQLite databases for projects, ingestion state, and diagrams; file-based KB indices on disk.

## Repository layout

- backend/ - FastAPI app, services, ingestion pipeline, agent system, diagram generation.
- frontend/ - React UI, hooks, and API clients.
- data/ - SQLite DBs and KB indices (runtime).
- scripts/ - helper scripts (optional).
- docs/ - reference docs for the current codebase.

## Adding features (high level)

1. Add or update backend routes and services.
2. Expose new API calls in `frontend/src/services/apiService.ts`.
3. Add UI components or pages in `frontend/src/components/` or `frontend/src/features/`.
4. Update docs for new endpoints or workflows.

For architecture, setup, and API details see the docs in this folder.
