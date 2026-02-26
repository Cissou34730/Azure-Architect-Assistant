## Plan: OpenAI Primary with Azure OpenAI Fallback Router

Implement a minimal provider-routing layer inside the existing AI abstraction so application code uses one AI interface while runtime routing handles OpenAI-first with Azure OpenAI fallback. Reuse the current `AIService` + provider interfaces, add Azure provider implementations, and route chat/embeddings/model-list through a single entry path. Fallback is triggered only for transient failures (timeouts, 429, 5xx).

**Steps**
1. Phase 1 — Baseline and contract hardening
   1. Add explicit routing/fallback configuration fields to `AIConfig` (primary provider, fallback provider, fallback enabled, fallback-on-transient-only) with safe defaults preserving current OpenAI behavior.
   2. Extend config validation to require Azure deployment settings only when Azure is selected as primary or fallback target.
   3. Keep existing external call sites stable by preserving `AIService.chat`, `AIService.complete`, `AIService.embed_text`, `AIService.embed_batch` method signatures.
2. Phase 2 — Provider parity (minimal Azure implementation)
   1. Add `AzureOpenAILLMProvider` implementing `LLMProvider` with API parity to current `OpenAILLMProvider` (chat + complete + stream behavior aligned where feasible).
   2. Add `AzureOpenAIEmbeddingProvider` implementing `EmbeddingProvider` and matching batching behavior expected by current embedding flows.
   3. Add shared Azure client singleton utility (parallel to `get_openai_client`) for connection reuse and consistent timeout/retry settings.
   4. Export new providers in providers package init for factory use.
3. Phase 3 — Single-call router (core requirement)
   1. Introduce a small `AIRouter`/`FailoverProvider` in `backend/app/services/ai` that exposes one internal call path per capability (`chat`, `complete`, `embed`) and performs OpenAI → Azure routing.
   2. Route logic: attempt primary provider first; on transient provider exceptions only (timeout, rate-limit, retriable 5xx), call fallback provider; otherwise re-raise primary error.
   3. Integrate router in `AIService` so app code keeps a single interface call and does not choose providers directly.
4. Phase 4 — Route all current OpenAI call paths
   1. Update `ModelsService` to use router-aware model listing strategy instead of hard-coded OpenAI client call; for Azure fallback, resolve models from configured deployment metadata (or a constrained compatibility list) rather than relying on unsupported Azure model listing semantics.
   2. Update LangGraph native agent path to consume chat LLM via `AIService.create_chat_llm`/router-aware factory instead of direct `ChatOpenAI(...)` construction.
   3. Update model probe endpoint in `models_router.py` to use routed provider strategy (same runtime compatibility path as inference).
5. Phase 5 — TDD coverage (no execution unless requested)
   1. Add regression tests for router behavior: primary success path, transient failure fallback success, non-transient failure no-fallback, fallback failure propagation.
   2. Add provider factory tests for OpenAI primary + Azure fallback combinations and invalid config matrix.
   3. Add targeted tests for LangGraph path wiring and models endpoint routing behavior.
6. Phase 6 — Documentation and Azure request configuration
   1. Update backend docs to document env vars and routing behavior for OpenAI primary + Azure fallback.
   2. Add explicit Azure OpenAI setup section: endpoint, API version, deployment names, and model-to-deployment mapping needed for requests.
   3. Update docs index links if a new backend provider-routing doc is added.

**Relevant files**
- `c:/Users/cyril.beurier/code/Azure-Architect-Assistant-archchatbot/backend/app/services/ai/config.py` — extend routing/fallback config and validation logic.
- `c:/Users/cyril.beurier/code/Azure-Architect-Assistant-archchatbot/backend/app/services/ai/ai_service.py` — inject router while preserving public interface.
- `c:/Users/cyril.beurier/code/Azure-Architect-Assistant-archchatbot/backend/app/services/ai/interfaces.py` — keep capability contracts unchanged; only extend if required for model listing abstraction.
- `c:/Users/cyril.beurier/code/Azure-Architect-Assistant-archchatbot/backend/app/services/ai/providers/openai_llm.py` — reuse as primary provider implementation.
- `c:/Users/cyril.beurier/code/Azure-Architect-Assistant-archchatbot/backend/app/services/ai/providers/openai_embedding.py` — reuse for embedding primary.
- `c:/Users/cyril.beurier/code/Azure-Architect-Assistant-archchatbot/backend/app/services/ai/providers/openai_client.py` — reference singleton/client config pattern.
- `c:/Users/cyril.beurier/code/Azure-Architect-Assistant-archchatbot/backend/app/services/ai/providers/__init__.py` — register Azure providers and client helpers.
- `c:/Users/cyril.beurier/code/Azure-Architect-Assistant-archchatbot/backend/app/services/models_service.py` — replace direct OpenAI model listing dependency with routed strategy.
- `c:/Users/cyril.beurier/code/Azure-Architect-Assistant-archchatbot/backend/app/agents_system/langgraph/nodes/agent_native.py` — remove direct `ChatOpenAI` construction path; unify through AI service.
- `c:/Users/cyril.beurier/code/Azure-Architect-Assistant-archchatbot/backend/app/routers/settings/models_router.py` — probe model compatibility through routed AI path.
- `c:/Users/cyril.beurier/code/Azure-Architect-Assistant-archchatbot/backend/tests/services/test_openai_llm_provider.py` — pattern reference for provider-level tests.
- `c:/Users/cyril.beurier/code/Azure-Architect-Assistant-archchatbot/docs/backend/BACKEND_REFERENCE.md` — update provider abstraction and singleton notes.
- `c:/Users/cyril.beurier/code/Azure-Architect-Assistant-archchatbot/docs/DEVELOPMENT_GUIDE.md` — add configuration guidance for fallback and Azure deployments.
- `c:/Users/cyril.beurier/code/Azure-Architect-Assistant-archchatbot/docs/README.md` — keep docs navigation accurate if new doc is introduced.

**Verification**
1. Static verification checklist
   1. Confirm no app call site directly imports/constructs OpenAI clients for chat/embeddings/model-list outside provider/router layer.
   2. Confirm `AIService` remains single public API entry for LLM and embedding operations.
2. Automated verification (to be executed only on user request)
   1. Run targeted tests for router and provider integration (`backend/tests/services/...`).
   2. Run backend unit test task if requested.
3. Manual verification
   1. Configure OpenAI key + Azure endpoint/deployments in env.
   2. Simulate transient OpenAI failure and verify request succeeds through Azure fallback.
   3. Verify non-transient OpenAI errors do not fallback.
   4. Verify LangGraph agent path still functions through unified AI interface.

**Decisions**
- Fallback trigger: transient failures only (timeouts, 429, retriable 5xx), not broad fallback for all exceptions.
- Scope includes chat/completions, embeddings, and model-list endpoint routing.
- LangGraph direct OpenAI usage is in-scope and should be unified through AI service.
- Minimal-change principle: preserve existing method signatures and call sites where possible; add a small router layer rather than broad refactor.

**Further Considerations**
1. Azure model listing behavior differs from OpenAI model listing; recommendation is deployment-driven model metadata from config for deterministic behavior.
2. If streaming fallback is needed mid-stream, safest minimal behavior is fallback only before stream starts; avoid switching providers after tokens begin.