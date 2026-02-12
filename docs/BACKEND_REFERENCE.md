# Backend Reference

## Entry points and layout

- App entry: `backend/app/main.py`
- Lifecycle: `backend/app/lifecycle.py`
- Routers: `backend/app/routers/`
- Services: `backend/app/services/`
- Ingestion pipeline: `backend/app/ingestion/`
- Agent system: `backend/app/agents_system/`
- Diagram generation: `backend/app/services/diagram/`
- SQLAlchemy models: `backend/app/models/`

## Router conventions

- `kb_management/` and `kb_query/` use a models + operations + router pattern.
- `project_management/` uses a router with services in `project_management/services/`.
- `ingestion.py` is a dedicated router because it owns background tasks.
- Diagram routes live under `routers/diagram_generation/` with a `/api/v1` prefix.

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
- App settings live in `backend/app/core/config.py` (extra env keys must be added there).
- `backend/config/ingestion.config.json` controls ingest queue behavior.
- `backend/config/kb_defaults.json` provides chunking and embedding defaults.
- `backend/config/mcp/mcp_config.json` configures MCP servers.
- `backend/config/prompts/agent_prompts.yaml` defines agent prompts.

## Singleton Pattern Usage

The backend uses singletons for expensive, shared resources with lifecycle management needs.

### Current Singletons

| Service | Location | Justification | Performance Impact |
|---------|----------|---------------|-------------------|
| **AgentRunner** | `app/agents_system/runner.py` | Lifecycle coordination, task tracking, graceful shutdown | Startup: 2-3s (MCP + LLM init) |
| **KBManager** | `app/service_registry.py` | Vector index caching (150MB in memory), preloaded at startup | 3.2s load time per KB, indices cached in memory |
| **LLMService** | `app/services/llm_service.py` | Connection pooling to OpenAI/Azure | HTTP client reuse, rate limiting |
| **AIService** | `app/services/ai/ai_service.py` | Provider abstraction (OpenAI, Azure, Anthropic) | Model caching, connection pooling |
| **PromptLoader** | `app/agents_system/config/prompt_loader.py` | File I/O caching for YAML prompts | Avoids repeated disk reads |

### Accessing Singletons

**✅ Recommended**: Use FastAPI dependency injection for testability:

```python
from fastapi import Depends
from app.dependencies import get_kb_manager

@router.get("/kbs")
async def list_kbs(kb_manager: KBManager = Depends(get_kb_manager)):
    return kb_manager.list_kbs()
```

**❌ Avoid**: Direct singleton access (harder to test):

```python
# Don't do this in routes
kb_manager = ServiceRegistry.get_kb_manager()
```

### Testing with Singletons

All singletons support dependency override for testing:

```python
from app.dependencies import get_kb_manager

def test_my_route(client, mock_kb_manager):
    app.dependency_overrides[get_kb_manager] = lambda: mock_kb_manager
    # ... test code ...
    app.dependency_overrides.clear()
```

See [Testing Guide](backend/TESTING_DEPENDENCY_INJECTION.md) for comprehensive examples.

### Design Rationale

See [Singleton Pattern Analysis](reviews/SINGLETON_PATTERN_ANALYSIS.md) for detailed architectural rationale and alternatives considered.

**Key Benefits**:
- **Performance**: 150MB indices loaded once, not per-request (100 req/min = 320s CPU without singleton)
- **Lifecycle**: Coordinated startup/shutdown prevents resource leaks
- **Consistency**: All requests see same state (KB updates, agent orchestrator)
- **Testability**: FastAPI dependency injection enables easy mocking


## Adding a new backend feature

1. Decide the feature area (projects, KB, ingestion, agent, diagrams) and create a router module under `backend/app/routers/`.
2. Define request/response models (Pydantic) near the router or in a `*_models.py` file.
3. Implement business logic in a service or operations module.
4. Register the router in `backend/app/main.py`.
5. Add or update frontend calls in `frontend/src/services/apiService.ts` and align types.

## Adding or changing persistence

- Add SQLAlchemy models in `backend/app/models/`.
- Create or update Alembic migrations in `backend/migrations/`.
- Update any service code that reads/writes the new tables.

## Extending ingestion

- Add a source handler in `backend/app/ingestion/domain/sources/` and register it in `factory.py`.
- Update KB configuration to include the new source type.
- If the UI needs new fields, update `frontend/src/utils/ingestionConfig.ts`.

## Extending the agent system

- Add tools in `backend/app/agents_system/tools/`.
- Wire tool usage in the agent runner and update prompts if needed.
- Ensure MCP config is present in `backend/config/mcp/mcp_config.json`.

## Extending diagrams

- Add new diagram types in `backend/app/models/diagram/diagram.py`.
- Update the generator in `backend/app/services/diagram/`.
- Update UI labels in `frontend/src/components/diagrams/DiagramSetViewer.tsx`.
