# Backend Reference

## Entry points and layout

- App entry: `backend/app/main.py`
- Routers: `backend/app/routers/`
- Services: `backend/app/services/`
- Ingestion pipeline: `backend/app/ingestion/`
- Agent system: `backend/app/agents_system/`
- Diagram generation: `backend/app/services/diagram/`

## API overview

### Health
- `GET /health` - service health.

### Projects
- `POST /api/projects`
- `GET /api/projects`
- `GET /api/projects/{project_id}`
- `PUT /api/projects/{project_id}/requirements`
- `POST /api/projects/{project_id}/documents`
- `POST /api/projects/{project_id}/analyze-docs`
- `POST /api/projects/{project_id}/chat`
- `GET /api/projects/{project_id}/state`
- `GET /api/projects/{project_id}/messages`
- `GET /api/projects/{project_id}/architecture/proposal` (SSE)

### Knowledge base management
- `POST /api/kb/create`
- `GET /api/kb/list`
- `GET /api/kb/health`
- `GET /api/kb/{kb_id}/status`
- `DELETE /api/kb/{kb_id}`

### Ingestion (orchestrator)
- `POST /api/ingestion/kb/{kb_id}/start`
- `POST /api/ingestion/kb/{kb_id}/pause`
- `POST /api/ingestion/kb/{kb_id}/resume`
- `POST /api/ingestion/kb/{kb_id}/cancel`
- `GET /api/ingestion/kb/{job_id}/status`
- `GET /api/ingestion/kb/{kb_id}/details`
- `GET /api/ingestion/kb/{kb_id}/job-view`

### KB queries
- `POST /api/query` (legacy)
- `POST /api/query/chat`
- `POST /api/query/proposal`
- `POST /api/query/kb-query`

### Agent chat
- `POST /api/agent/chat`
- `POST /api/agent/projects/{project_id}/chat`
- `GET /api/agent/projects/{project_id}/history`
- `GET /api/agent/health`
- `GET /api/agent/capabilities`

### Diagram generation
- `POST /api/v1/diagram-sets`
- `GET /api/v1/diagram-sets/{diagram_set_id}`

## Data models (high level)

- Project: name, requirements, created/updated timestamps.
- Project state: structured context, NFRs, constraints, open questions.
- Knowledge base: config in `data/knowledge_bases/config.json` with per-KB settings.
- Diagram set: input description, diagrams, ambiguities, stored in `data/diagrams.db`.

## Configuration and settings

- `.env` (repo root) provides ports, API keys, and storage paths.
- `backend/config/ingestion.config.json` controls ingest queue behavior.
- `backend/config/kb_defaults.json` provides chunking and embedding defaults.
- `backend/config/mcp/mcp_config.json` configures MCP servers.
- `backend/config/prompts/agent_prompts.yaml` defines agent prompts.

## Key services to know

- `app/services/ai/` - LLM and embedding adapters.
- `app/services/kb/` - multi-KB query orchestration.
- `app/ingestion/application/orchestrator.py` - ingestion pipeline controller.
- `app/services/diagram/` - diagram generation, validation, storage.
