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
4. Multi-agent routing selects specialized sub-agents based on request type.

Primary code:
- `backend/app/agents_system/`
- `backend/config/prompts/agent_prompts.yaml`
- `backend/config/mcp/mcp_config.json`
- `frontend/src/components/agent/`

#### Multi-Agent System (Phase 2 & 3)

The agent system uses a multi-agent architecture with intelligent routing to specialized sub-agents:

**Agent Routing Priority** (highest to lowest):
1. **IaC Generator** - Terraform/Bicep code generation
2. **Architecture Planner** - Complex architecture design with NFR analysis
3. **SaaS Advisor** - Multi-tenant SaaS architecture guidance (Phase 3)
4. **Cost Estimator** - Azure cost estimation and optimization (Phase 3)
5. **Main Agent** - General conversational guidance and orchestration

**Routing Flow**:
```
User Request → Agent Router → [Check IaC keywords + architecture exists?]
                           → [Check architecture keywords + complexity?]
                           → [Check SaaS keywords (strict)?]
                           → [Check cost keywords + architecture exists?]
                           → [Default: Main Agent]
```

**Specialized Agents**:

- **Architecture Planner Sub-Agent** (Phase 2)
  - Triggers: "architecture", "design", "proposal" + complexity indicators (multi-region, HA, DR, compliance, microservices)
  - Capabilities: complete architecture design, C4 diagrams (System Context, Container), functional flow diagrams, comprehensive NFR analysis
  - Prompt: `backend/config/prompts/architecture_planner_prompt.yaml` (160 lines)
  - Node: `backend/app/agents_system/langgraph/nodes/architecture_planner.py`

- **IaC Generator Sub-Agent** (Phase 2)
  - Triggers: "terraform", "bicep", "iac" + finalized architecture (candidateArchitectures exists)
  - Capabilities: production-ready Bicep/Terraform code, resource schema validation, parameterization, dependency management
  - Prompt: `backend/config/prompts/iac_generator_prompt.yaml` (175 lines)
  - Node: `backend/app/agents_system/langgraph/nodes/iac_generator.py`

- **SaaS Advisor Sub-Agent** (Phase 3)
  - Triggers: "saas", "multi-tenant", "B2B/B2C", "tenant isolation", suitability questions ("should this be SaaS?")
  - Capabilities: tenant models (Silo/Pool/Bridge), isolation strategies (data/compute/network/storage), B2B vs B2C patterns, noisy neighbor mitigation, deployment stamps, per-tenant cost analysis
  - Prompt: `backend/config/prompts/saas_advisor_prompt.yaml` (393 lines)
  - Node: `backend/app/agents_system/langgraph/nodes/saas_advisor.py`
  - Routing: LOW priority (after IaC and Architecture), strict keyword matching only

- **Cost Estimator Sub-Agent** (Phase 3)
  - Triggers: "cost", "price", "pricing", "how much", "TCO", "budget estimate" + finalized architecture
  - Capabilities: Azure Retail Prices API integration, cost formulas (monthly/annual/3-year TCO), regional pricing (+15% West Europe, +30% Brazil South), optimization strategies (RIs 40-60%, right-sizing, AHB 30-55%, spot 70-90%)
  - Prompt: `backend/config/prompts/cost_estimator_prompt.yaml` (349 lines)
  - Node: `backend/app/agents_system/langgraph/nodes/cost_estimator.py`
  - Pricing Client: `backend/app/services/pricing/retail_prices_client.py` (async, retry logic, pagination)
  - Routing: LOWEST priority (after IaC, Architecture, SaaS), requires finalized architecture

**Routing Implementation**:
- `backend/app/agents_system/langgraph/nodes/stage_routing.py`: routing functions (should_route_to_*, prepare_*_handoff)
- `backend/app/agents_system/langgraph/graph_factory.py`: LangGraph workflow with conditional edges
- `backend/app/agents_system/langgraph/state.py`: GraphState with agent_handoff_context, routing_decision, saas_context, cost_estimate

**Testing**:
- `scripts/test_phase3_saas_advisor.py`: 4 scenarios, 100% passing
- `scripts/test_phase3_cost_estimator.py`: 4 scenarios, 100% passing
- `scripts/test_phase3_full_system.py`: 8 scenarios, 100% passing (routing priority, false positives)

See [AGENT_ACTIVATION_GUIDE.md](./AGENT_ACTIVATION_GUIDE.md) for user-facing activation guide.

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
