## Plan: Unify AI Provider Routing

Build a single provider-neutral AI orchestration layer around AIService so every LLM and embedding call goes through one contract, OpenAI-to-Azure fallback works consistently, Azure-only deployments are valid, and future providers can be added without rewriting callers.

**Implementation status (2026-03-09)**
1. Completed: LangGraph now gets its native chat model from `AIService.create_chat_llm()`, and agent startup/health checks validate the selected AI provider configuration instead of requiring OpenAI specifically.
2. Completed: Azure model probing now validates the requested deployment during model switching.
3. Completed: KB defaults, KB management request defaults, ingestion embedding, vector indexing metadata, and LlamaIndex adapter defaults now resolve from the active AI provider configuration instead of OpenAI-only settings names.
4. Completed: The active ingestion embedder path now delegates to `AIService.embed_text()` rather than constructing `OpenAIEmbedding` directly.
5. Completed: Backend docs were updated to match the current runtime behavior.

**Validated current-state findings**
1. Resolved: [backend/app/agents_system/langgraph/nodes/agent_native.py](backend/app/agents_system/langgraph/nodes/agent_native.py#L19) no longer owns provider selection for the native chat model.
2. Resolved: [backend/app/agents_system/runner.py](backend/app/agents_system/runner.py#L57) no longer blocks Azure-only deployments on an OpenAI-specific readiness check.
3. Resolved: [backend/app/services/settings_models_service.py](backend/app/services/settings_models_service.py#L43) now rewrites Azure deployment probes correctly.
4. Resolved: [docs/backend/AI_PROVIDER_ROUTING.md](docs/backend/AI_PROVIDER_ROUTING.md#L79) now matches the current LangGraph runtime wiring.

**Phase 1: Define the contract**
1. Make AIService the only orchestration surface for chat, complete, embed_text, embed_batch, provider-aware model metadata, native LangGraph adapter creation, and model probing/reinitialization.
2. Keep provider selection, credential resolution, fallback policy, and model identity inside the AI layer instead of letting agents, KB, or ingestion code branch on OpenAI versus Azure.
3. Decide the fallback shape up front.
Recommendation: support separate LLM and embedding fallback semantics in the design, even if implementation is staged.

**Phase 2: Fix the highest-risk runtime bypasses**
1. Replace direct ChatOpenAI and AzureChatOpenAI construction in [backend/app/agents_system/langgraph/nodes/agent_native.py](backend/app/agents_system/langgraph/nodes/agent_native.py#L19) and [backend/app/agents_system/langgraph/nodes/agent_native.py](backend/app/agents_system/langgraph/nodes/agent_native.py#L227) with an AIService-owned native adapter factory.
2. Update [backend/app/agents_system/runner.py](backend/app/agents_system/runner.py#L57) so startup and health checks validate the configured provider set instead of requiring OpenAI specifically.
3. Treat LangGraph-native objects as adapter outputs from AIService, not as a second provider-routing implementation.
4. First implementation slice: land Phase 2 plus Azure-aware probing in [backend/app/services/settings_models_service.py](backend/app/services/settings_models_service.py#L43) before widening scope to KB and ingestion.

**Phase 3: Normalize embeddings and KB/ingestion**
1. Remove OpenAI-specific defaults and assumptions from [backend/app/kb/models.py](backend/app/kb/models.py#L19), [backend/app/ingestion/application/pipeline_components.py](backend/app/ingestion/application/pipeline_components.py), [backend/app/ingestion/infrastructure/indexing/vector.py](backend/app/ingestion/infrastructure/indexing/vector.py#L53), and any still-active embedder path such as [backend/app/ingestion/infrastructure/embedding/openai_embedder.py](backend/app/ingestion/infrastructure/embedding/openai_embedder.py#L41).
2. Route KB and ingestion embedding construction through provider-neutral AIService-backed adapters in [backend/app/services/ai/adapters/llamaindex.py](backend/app/services/ai/adapters/llamaindex.py).
3. Update request/default models in [backend/app/routers/kb_management/management_models.py](backend/app/routers/kb_management/management_models.py) so API contracts stop encoding OpenAI-only assumptions.

**Phase 4: Fix model management and lifecycle**
1. Correct Azure deployment probing and switching in [backend/app/services/settings_models_service.py](backend/app/services/settings_models_service.py#L43) so Azure validates the requested deployment, not just the current model.
2. Harden client lifecycle in [backend/app/services/ai/ai_service.py](backend/app/services/ai/ai_service.py), [backend/app/services/ai/providers/openai_client.py](backend/app/services/ai/providers/openai_client.py), and [backend/app/services/ai/providers/azure_openai_client.py](backend/app/services/ai/providers/azure_openai_client.py) so reinitialization resets stale provider clients and refreshes dependent singletons safely.
3. Revisit config ownership in [backend/app/services/ai/config.py](backend/app/services/ai/config.py) and [backend/app/core/app_settings.py](backend/app/core/app_settings.py#L106) so AppSettings remains the source of truth and legacy OpenAI compatibility helpers stop leaking into runtime paths.

**Phase 5: Tests and docs**
1. Add regression tests first for each non-trivial change:
[backend/tests/services/test_ai_router.py](backend/tests/services/test_ai_router.py#L52),
[backend/tests/services/test_ai_service_fallback_config.py](backend/tests/services/test_ai_service_fallback_config.py#L27),
[backend/tests/agents_system/test_langgraph_unified_workflow.py](backend/tests/agents_system/test_langgraph_unified_workflow.py#L56).
2. Add new coverage for Azure-only agent startup, LangGraph adapter routing through AIService, embedding fallback, KB/ingestion provider-neutral defaults, and Azure model-switch probing.
3. Update [docs/backend/AI_PROVIDER_ROUTING.md](docs/backend/AI_PROVIDER_ROUTING.md#L5), [docs/backend/AZURE_OPENAI_SETUP.md](docs/backend/AZURE_OPENAI_SETUP.md#L141), and [docs/README.md](docs/README.md) so the docs match the final runtime architecture.

**Relevant files**
- [backend/app/services/ai/ai_service.py](backend/app/services/ai/ai_service.py)
- [backend/app/services/ai/router.py](backend/app/services/ai/router.py)
- [backend/app/services/ai/config.py](backend/app/services/ai/config.py)
- [backend/app/core/app_settings.py](backend/app/core/app_settings.py)
- [backend/app/core/settings/ai.py](backend/app/core/settings/ai.py#L20)
- [backend/app/agents_system/langgraph/nodes/agent_native.py](backend/app/agents_system/langgraph/nodes/agent_native.py)
- [backend/app/agents_system/runner.py](backend/app/agents_system/runner.py)
- [backend/app/services/settings_models_service.py](backend/app/services/settings_models_service.py)
- [backend/app/services/models_service.py](backend/app/services/models_service.py)
- [backend/app/services/ai/adapters/llamaindex.py](backend/app/services/ai/adapters/llamaindex.py)
- [backend/app/kb/models.py](backend/app/kb/models.py)
- [backend/app/kb/service.py](backend/app/kb/service.py)
- [backend/app/ingestion/application/pipeline_components.py](backend/app/ingestion/application/pipeline_components.py)
- [backend/app/ingestion/infrastructure/indexing/vector.py](backend/app/ingestion/infrastructure/indexing/vector.py)
- [backend/app/ingestion/infrastructure/embedding/openai_embedder.py](backend/app/ingestion/infrastructure/embedding/openai_embedder.py)
- [backend/app/routers/kb_management/management_models.py](backend/app/routers/kb_management/management_models.py)
- [docs/backend/AI_PROVIDER_ROUTING.md](docs/backend/AI_PROVIDER_ROUTING.md)
- [docs/backend/AZURE_OPENAI_SETUP.md](docs/backend/AZURE_OPENAI_SETUP.md)

**Verification**
1. Red tests for LangGraph routing, Azure-only startup, embedding fallback, and Azure model probing.
2. Green implementation for agent path first, then embeddings/KB, then lifecycle/model switching.
3. Manual validation for four scenarios: Azure-only runtime, OpenAI primary with Azure fallback for chat, OpenAI primary with Azure fallback for embeddings, and LangGraph tool execution under each supported provider path.
4. Final doc review to ensure runtime claims exactly match the code.

**Decisions**
- Included: backend AI orchestration, agents, ingestion, KB, model management, tests, and docs.
- Excluded: new providers beyond OpenAI and Azure, unrelated prompt/business-logic refactors, frontend work.
- Recommended sequencing: tests first, then agent/runtime correctness, then embeddings and KB defaults, then lifecycle/config cleanup, then docs.

The full version is saved in session memory at /memories/session/plan.md.

1. If you want, I can refine this into a milestone-based execution plan with estimated effort per phase.
2. If you approve this shape, the next step is to hand off Phase 1 plus Phase 2 as the first implementation slice.
