# System Architecture

## Purpose

Comprehensive human-oriented architecture reference for runtime topology, layering, and data flows.

## Design goals

- Keep one backend as the system of record for API, state, and long-running jobs.
- Keep feature areas modular (projects, KB, agent, diagrams) with clear boundaries.
- Persist job and project state so the UI can reconnect without losing progress.

## Runtime topology

Frontend (React + Vite) -> FastAPI backend -> OpenAI / LlamaIndex / MCP

- The frontend calls the backend at `BACKEND_URL` (default `http://localhost:8000`).
- The backend owns all business logic: project management, KB ingestion/query, agent chat, and diagram generation.

## Backend layering and boundaries

- Canonical feature API surface lives under `backend/app/features/`.
- Shared runtime infrastructure lives under `backend/app/shared/`.
- `backend/app/agents_system/` remains the orchestration/platform layer and is allowed to depend on feature contracts.
- `backend/app/routers/`, `backend/app/services/`, and `backend/app/core/` remain compatibility and not-yet-migrated areas for non-project capabilities.

### Backend target ownership

- `backend/app/features/projects/` owns project CRUD, workspace composition, project state compatibility reads, and the canonical `/api/projects/{project_id}/workspace` surface.
- `backend/app/features/agent/`, `checklists/`, `knowledge/`, `ingestion/`, `diagrams/`, and `settings/` provide feature contracts and canonical API ownership where carve-out work has landed.
- `backend/app/shared/{config,db,ai,mcp,logging}` owns cross-cutting runtime concerns.

## Frontend layering and boundaries

- `frontend/src/app/` owns shell layout, route wiring, and the static workspace registry.
- `frontend/src/features/` owns feature-local pages, API clients, hooks, types, and workspace manifests.
- `frontend/src/shared/` owns reusable UI, shared hooks, HTTP helpers, config, and utilities.
- Root `frontend/src/{hooks,services,types}` compatibility shims have been removed.

### Workspace composition

- Workspaces are registered statically in `frontend/src/app/workspaceRegistry.ts`.
- Each feature exposes a `workspace.manifest.ts` that describes route metadata and, where applicable, workspace shell/tab ownership.
- The projects workspace uses a manifest-driven tab registry rather than hardcoded tab-switch logic.

## Startup and lifecycle

- `backend/app/lifecycle.py` initializes the project DB, ingestion DB, and diagram DB.
- KB configs load at startup; indices are loaded lazily on first query.
- Agent startup initializes an MCP client; if it fails, agent endpoints remain unavailable.

## Key data flows

### Project lifecycle

1. Create a project and add requirements or documents.
2. Analyze documents to produce structured project state.
3. Read the composed workspace view from `/api/projects/{project_id}/workspace`.
4. Chat updates state and stores conversation history.
5. Proposal generation streams progress and returns a final proposal.

Primary code:

- `backend/app/features/projects/api/`
- `backend/app/features/projects/application/workspace_composer.py`
- `backend/app/features/projects/infrastructure/`
- `frontend/src/features/projects/`

### Project state composition and persistence

- `ProjectState.state` is no longer the canonical store for architecture inputs or the main AAA artifact families.
- Architecture inputs now live in `project_architecture_inputs`.
- Stable top-level artifact families now live in `project_state_components`.
- Canonical reads merge decomposed storage back into a compatibility `projectState` payload for both `/workspace` and the deprecated `/state` route.
- `/api/projects/{project_id}/state` is now a compatibility read sourced from the workspace composer and returned with `Deprecation`, `Sunset`, and `Link` headers.

### KB ingestion pipeline

1. Load source documents (web or files).
2. Chunk content.
3. Embed chunks with OpenAI embeddings.
4. Index vectors for fast query.
5. Persist job status and phase progress for UI updates.

Primary code:

- `backend/app/ingestion/application/orchestrator.py`
- `backend/app/routers/ingestion.py`
- `backend/app/ingestion/domain/`
- `frontend/src/features/ingestion/`

### KB query pipeline

1. Select KBs (chat or proposal profile).
2. Run vector search via LlamaIndex.
3. Merge results across KBs and generate an answer with citations.

Primary code:

- `backend/app/services/kb/`
- `backend/app/routers/kb_query/`
- `frontend/src/features/knowledge/`

### Agent chat

1. MCP client searches Microsoft Learn and code samples.
2. Agent applies ReAct steps and synthesizes an answer.
3. Optional project-aware chat updates project state.
4. Multi-agent routing selects specialized sub-agents based on request type.

Primary code:

- `backend/app/agents_system/`
- `backend/config/prompts/agent_prompts.yaml`
- `backend/config/mcp/mcp_config.json`
- `frontend/src/features/agent/`

### Diagram generation

1. Create a diagram set from a text description.
2. Detect ambiguities.
3. Generate Mermaid-based functional, C4 context, and C4 container diagrams.
4. Store diagrams in the diagrams database.

Primary code:

- `backend/app/services/diagram/`
- `backend/app/routers/diagram_generation/`
- `backend/app/models/diagram/`
- `frontend/src/features/diagrams/`

## Storage

- Projects: SQLite at `data/projects.db`.
- Ingestion jobs and phases: SQLite at `data/ingestion.db`.
- Diagram sets: SQLite at `data/diagrams.db`.
- KB indices: `data/knowledge_bases/<kb_id>/`.

## Configuration

- `.env` in repo root supplies ports, API keys, and storage paths.
- `backend/app/shared/config/app_settings.py` is the canonical AppSettings entry point; add new env-backed settings via the `backend/app/core/settings/` mixins and consume them through `AppSettings`.
- `backend/config/ingestion.config.json` and `backend/config/kb_defaults.json` tune ingestion defaults.
- `backend/config/prompts/agent_prompts.yaml` controls agent behavior.

## Extension points

- New API feature: add the capability under `backend/app/features/<feature>/`, expose the HTTP surface from the feature API package, register it in `backend/app/main.py`, then add the corresponding frontend feature API client under `frontend/src/features/<feature>/api/`.
- New KB source: add a handler in `backend/app/ingestion/domain/sources/` and register it in the source factory.
- New agent tool: keep registration/factory code in `backend/app/agents_system/tools/` and place feature-owned tool logic with the owning feature when practical.
- New diagram type: update `backend/app/models/diagram/diagram.py` and the diagram generator and UI labels.

---

**Status**: Active  
**Last Updated**: 2026-04-02  
**Owner**: Engineering
