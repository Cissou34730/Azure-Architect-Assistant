# System Architecture

## Runtime topology

Frontend (React + Vite) -> FastAPI backend -> OpenAI / LlamaIndex / MCP

- The frontend calls the backend at `BACKEND_URL` (default http://localhost:8000).
- The backend owns all business logic: project management, KB ingestion/query, agent chat, and diagram generation.

## Backend structure

- `backend/app/main.py` wires the API routers and lifecycle hooks.
- `backend/app/routers/` holds route modules:
  - `project_management/` (projects, documents, chat, proposals)
  - `kb_management/` (KB create, list, health, status)
  - `kb_query/` (query endpoints)
  - `ingestion.py` (orchestrated ingestion jobs)
  - `diagram_generation/` (diagram sets)
  - `agents_system/agents/router.py` (agent chat)
- `backend/app/services/` holds business logic (AI, KB query, diagrams, MCP).
- `backend/app/ingestion/` implements the ingestion pipeline and persistence.

## Key data flows

### Project lifecycle
1. Create project and add requirements or documents.
2. Analyze documents to produce a structured project state.
3. Chat updates the state and stores conversation history.
4. Proposal generation streams progress and returns a final proposal.

### KB ingestion pipeline
1. Load source documents (web or files).
2. Chunk content.
3. Embed chunks with OpenAI embeddings.
4. Index vectors for fast query.
5. Persist job status and phase progress for UI updates.

### KB query pipeline
1. Select KBs (chat or proposal profile).
2. Run vector search via LlamaIndex.
3. Merge results across KBs and generate an answer with citations.

### Agent chat
1. MCP client searches Microsoft Learn and code samples.
2. Agent applies ReAct steps and synthesizes an answer.
3. Optional project-aware chat updates project state.

### Diagram generation
1. Create a diagram set from a text description.
2. Detect ambiguities.
3. Generate Mermaid-based functional, C4 context, and C4 container diagrams.
4. Store diagrams in the diagrams database.

## Storage

- Projects: SQLite at `data/projects.db`.
- Ingestion jobs and phases: SQLite at `data/ingestion.db`.
- Diagram sets: SQLite at `data/diagrams.db`.
- KB indices: `data/knowledge_bases/<kb_id>/`.

## Configuration

- `.env` in repo root supplies ports, OpenAI keys, and storage paths.
- `backend/config/*.json` holds ingestion and KB defaults.
- `backend/config/prompts/agent_prompts.yaml` controls agent prompts.
