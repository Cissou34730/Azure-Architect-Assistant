# System Architecture

## Design goals

- Keep one backend as the system of record for API, state, and long-running jobs.
- Keep feature areas modular (projects, KB, agent, diagrams) with clear boundaries.
- Persist job and project state so the UI can reconnect without losing progress.

## Runtime topology

Frontend (React + Vite) -> FastAPI backend -> OpenAI / LlamaIndex / MCP

- The frontend calls the backend at `BACKEND_URL` (default http://localhost:8000).
- The backend owns all business logic: project management, KB ingestion/query, agent chat, and diagram generation.

## Backend layering and boundaries

- API layer: `backend/app/routers/` (request parsing, response shapes, routing).
- Service layer: `backend/app/services/` plus feature services under router modules.
- Domain and persistence: `backend/app/models/`, `backend/app/ingestion/`, `backend/app/kb/`.
- Cross-cutting: `backend/app/core/config.py`, `backend/app/core/logging.py`, `backend/app/lifecycle.py`.

## Startup and lifecycle

- `backend/app/lifecycle.py` initializes the project DB, ingestion DB, and diagram DB.
- KB configs load at startup; indices are loaded lazily on first query.
- Agent startup initializes an MCP client; if it fails, agent endpoints remain unavailable.

## Key data flows

### Project lifecycle
1. Create a project and add requirements or documents.
2. Analyze documents to produce structured project state.
3. Chat updates state and stores conversation history.
4. Proposal generation streams progress and returns a final proposal.

Primary code:
- `backend/app/routers/project_management/`
- `backend/app/routers/project_management/services/`
- `frontend/src/features/projects/`

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
- `frontend/src/components/ingestion/`

### KB query pipeline
1. Select KBs (chat or proposal profile).
2. Run vector search via LlamaIndex.
3. Merge results across KBs and generate an answer with citations.

Primary code:
- `backend/app/services/kb/`
- `backend/app/routers/kb_query/`
- `frontend/src/components/kb/`

### Agent chat
1. MCP client searches Microsoft Learn and code samples.
2. Agent applies ReAct steps and synthesizes an answer.
3. Optional project-aware chat updates project state.

Primary code:
- `backend/app/agents_system/`
- `backend/config/prompts/agent_prompts.yaml`
- `backend/config/mcp/mcp_config.json`
- `frontend/src/components/agent/`

### Diagram generation
1. Create a diagram set from a text description.
2. Detect ambiguities.
3. Generate Mermaid-based functional, C4 context, and C4 container diagrams.
4. Store diagrams in the diagrams database.

Primary code:
- `backend/app/services/diagram/`
- `backend/app/routers/diagram_generation/`
- `backend/app/models/diagram/`
- `frontend/src/components/diagrams/`

## Storage

- Projects: SQLite at `data/projects.db`.
- Ingestion jobs and phases: SQLite at `data/ingestion.db`.
- Diagram sets: SQLite at `data/diagrams.db`.
- KB indices: `data/knowledge_bases/<kb_id>/`.

## Configuration

- `.env` in repo root supplies ports, API keys, and storage paths.
- `backend/app/core/config.py` defines AppSettings; add new env keys there.
- `backend/config/ingestion.config.json` and `backend/config/kb_defaults.json` tune ingestion defaults.
- `backend/config/prompts/agent_prompts.yaml` controls agent behavior.

## Extension points

- New API feature: add a router module, service logic, register it in `backend/app/main.py`, then expose it via `frontend/src/services/apiService.ts`.
- New KB source: add a handler in `backend/app/ingestion/domain/sources/` and register it in the source factory.
- New agent tool: add tool logic in `backend/app/agents_system/tools/` and wire it in the runner.
- New diagram type: update `backend/app/models/diagram/diagram.py` and the diagram generator and UI labels.
