# Azure AI Foundry Migration Plan (v2 — revised April 2026)

> **Status**: Implemented. Azure runtime/provider selection now uses `foundry`, dynamic deployment discovery, and Azure AI Foundry documentation.

## Goal

Replace the `"azure"` LLM/embedding provider (Azure OpenAI data-plane APIs, static deployment config) with a new `"foundry"` provider that discovers **all** deployed models dynamically from the consolidated AIServices account (`cyril-mnxb63o4-eastus2`) — including OpenAI, xAI, DeepSeek, and Microsoft model formats. Inference stays OpenAI-compatible (`AzureChatOpenAI` unchanged). Features are identical: refresh model list, select model, chat assistant, embeddings.

---

## Context

### Azure Resources (final consolidated state)

| Property | Value |
|---|---|
| Account | `cyril-mnxb63o4-eastus2` (kind: AIServices) |
| Region | East US 2 |
| Resource group | `aaa` |
| Endpoint | `https://cyril-mnxb63o4-eastus2.cognitiveservices.azure.com/` |
| Project | `cyril-mnxb63o4-eastus2_project` |

### Deployed Models (11 total)

| Deployment name | Model | Format |
|---|---|---|
| `gpt-5.3-chat` | gpt-5.3-chat | OpenAI |
| `text-embedding-3-small` | text-embedding-3-small | OpenAI |
| `aaadp` | gpt-4o-mini | OpenAI |
| `gpt-5-mini` | gpt-5-mini | OpenAI |
| `gpt-5-pro` | gpt-5-pro | OpenAI |
| `gpt-5-chat` | gpt-5-chat | OpenAI |
| `gpt-54-mini` | gpt-5.4-mini | OpenAI |
| `gpt-54-nano` | gpt-5.4-nano | OpenAI |
| `grok-4-20-reasoning` | grok-4-20-reasoning | xAI |
| `DeepSeek-R1-0528` | DeepSeek-R1-0528 | DeepSeek |
| `Phi-4` | Phi-4 | Microsoft |

### Key Architectural Insight

AIServices endpoints expose **all** deployed models via the OpenAI-compatible chat completions API. Inference via `AzureChatOpenAI` works unchanged. The only thing that breaks is model **discovery** — the current `/openai/deployments` data-plane endpoint may not return non-OpenAI-format models. The fix is to use the Cognitive Services management-plane API for deployment listing.

---

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Auth | API key only | No Entra ID / `DefaultAzureCredential` complexity |
| Inference SDK | Keep `AzureChatOpenAI` from `langchain-openai` | Works against AIServices endpoints for all model formats |
| Model discovery | Cognitive Services management-plane REST API | Returns ALL formats (OpenAI, xAI, DeepSeek, Microsoft) |
| HTTP client | Raw `httpx` for management-plane calls | Avoids adding `azure-ai-projects` SDK dependency |
| Provider rename | `"azure"` → `"foundry"` | Clean break; no deprecated aliases kept |
| Fallback | None | Removed per user requirement; errors propagate directly |
| Static deployment config | None | `azure_llm_deployment` / `azure_llm_deployments` env vars eliminated |
| Embedding selection | Auto-detect from deployment list | First embedding-capable deployment unless user overrides |

> **Management-plane auth note**: The management API typically requires Azure AD auth, not API keys. If this is blocked, the fallback is to use the data-plane `/openai/deployments` endpoint and test whether AIServices returns non-OpenAI models there. **Recommendation**: Test data-plane first; only add management-plane if non-OpenAI models are missing from the response.

---

## New Environment Variables

| Env var | SecretKeeper key | Description |
|---|---|---|
| `AI_FOUNDRY_ENDPOINT` | `AI_FOUNDRY_ENDPOINT` | `https://cyril-mnxb63o4-eastus2.cognitiveservices.azure.com/` |
| `AI_FOUNDRY_API_KEY` | `AI_FOUNDRY_API_KEY` | API key for the AIServices account |
| `AI_FOUNDRY_API_VERSION` | — | Default: `"2024-10-21"` |
| `AI_FOUNDRY_RESOURCE_ID` | `AI_FOUNDRY_RESOURCE_ID` | ARM resource ID for management-plane discovery |

**Removed** (no longer needed):

- `AI_AZURE_OPENAI_ENDPOINT`
- `AI_AZURE_OPENAI_API_KEY`
- `AI_AZURE_OPENAI_API_VERSION`
- `AI_AZURE_LLM_DEPLOYMENT`
- `AI_AZURE_LLM_DEPLOYMENTS`
- `AI_AZURE_EMBEDDING_DEPLOYMENT`

---

## Implementation Phases

### Phase 1 — Config Layer *(foundation; blocks all other phases)*

**1. `AISettingsMixin`** (`backend/app/shared/config/settings/ai.py`)
- **Add**: `ai_foundry_endpoint`, `ai_foundry_api_key`, `ai_foundry_api_version` (default `"2024-10-21"`), `ai_foundry_resource_id`
- **Remove**: `ai_azure_llm_deployment`, `ai_azure_llm_deployments`

**2. `AIConfig`** (`backend/app/shared/ai/config.py`)
- **Add** fields: `foundry_endpoint`, `foundry_api_key`, `foundry_api_version`, `foundry_resource_id`
- **Add** `"foundry"` to `llm_provider` and `embedding_provider` Literal types
- **Remove** `"azure"` from Literal types
- **Remove** fields: `azure_openai_endpoint`, `azure_openai_api_key`, `azure_openai_api_version`, `azure_llm_deployment`, `azure_llm_deployments`, `azure_embedding_deployment`
- **Remove** fallback fields: `fallback_enabled`, `fallback_provider`, etc.
- Update `active_llm_model` property and `from_settings()` mapping
- Update `validate_provider_config()` for foundry

**3. `AppSettings`** (`backend/app/shared/config/app_settings.py`)
- **Add** `effective_foundry_endpoint`, `effective_foundry_api_key`, `effective_foundry_resource_id` with SecretKeeper resolution
- **Remove** `effective_azure_openai_endpoint`, `effective_azure_openai_api_key`, `effective_azure_llm_deployment`, `effective_azure_llm_deployments`, `effective_azure_embedding_deployment`
- **Remove** `_configured_azure_llm_deployment_ids()` helper
- Update `runtime_ai_selection` handling for `"foundry"` provider

---

### Phase 2 — Provider Implementation *(depends on Phase 1)*

**4. Create `foundry_client.py`** (`backend/app/shared/ai/providers/foundry_client.py`)
- Singleton `AsyncAzureOpenAI` client (same pattern as `azure_openai_client.py`)
- Configured from `AIConfig.foundry_endpoint`, `foundry_api_key`, `foundry_api_version`
- Exports: `get_foundry_client(config)`, `reset_foundry_client()`

**5. Create `foundry_llm.py`** (`backend/app/shared/ai/providers/foundry_llm.py`)
- `FoundryLLMProvider(LLMProvider)` — inherits chat/complete from `OpenAILLMProvider`
- `list_runtime_models()` — calls `_fetch_deployments_management_plane()`
- `_fetch_deployments_management_plane()`:
  ```
  GET https://management.azure.com{foundry_resource_id}/deployments?api-version=2024-10-01
  ```
  - API key header auth (falls back to data-plane if 401)
  - Returns ALL deployment formats (OpenAI, xAI, DeepSeek, Microsoft)
  - Filters: `provisioningState == "Succeeded"`, excludes embedding-only models
  - Returns `[{"id": deployment_name, "model": model_name, "format": model_format}]`
- Reuse `_is_excluded_model()` logic from current `azure_openai_llm.py`

**6. Create `foundry_embedding.py`** (`backend/app/shared/ai/providers/foundry_embedding.py`)
- `FoundryEmbeddingProvider(OpenAIEmbeddingProvider)`
- Uses `get_foundry_client()` + deployment name for embedding model
- Discovery: filters management-plane results for embedding-capable deployments

**7. Delete old Azure OpenAI providers**
- Remove `azure_openai_client.py`, `azure_openai_llm.py`, `azure_openai_embedding.py`
- Update `providers/__init__.py` exports

---

### Phase 3 — Service Layer Wiring *(depends on Phase 1 + 2)*

**8. Update `AIService`** (`backend/app/shared/ai/ai_service.py`)
- `_create_llm_provider()`: replace `"azure"` branch with `"foundry"` → `FoundryLLMProvider`
- `_create_embedding_provider()`: replace `"azure"` branch with `"foundry"` → `FoundryEmbeddingProvider`
- `create_chat_llm()`: replace Azure branch with Foundry branch:
  ```python
  "foundry": AzureChatOpenAI(
      azure_deployment=<runtime_selected_model>,
      api_version=config.foundry_api_version,
      azure_endpoint=config.foundry_endpoint,
      api_key=config.foundry_api_key,
      temperature=...,
  )
  ```
- Remove fallback provider logic

**9. Update `AIRouter`** (`backend/app/shared/ai/router.py`)
- Remove fallback routing logic; simplify to direct delegation
- Remove `fallback_llm`, `fallback_embedding`, `fallback_enabled`, `fallback_on_transient_only` parameters

**10. Update `ModelsService`** (`backend/app/shared/ai/models_service.py`)
- Replace `_fetch_azure_deployments_data_plane()` with foundry provider's `list_runtime_models()`
- Remove `_configured_azure_deployments()` (no more static config)
- Update cache key generation for `"foundry"` provider

**11. Update `SettingsService`** (`backend/app/features/settings/application/settings_service.py`)
- Replace `"azure"` references with `"foundry"` in `_build_provider_payloads()`, `_build_probe_config()`, `set_selection()`
- `AIServiceManager._build_config_for_selection("foundry", model_id)`: stores selected model for runtime use
- Update `persist_runtime_ai_selection()` for `"foundry"`

---

### Phase 4 — Frontend Update *(parallel with Phase 3)*

**12. `settingsService.ts`** (`frontend/src/features/settings/api/settingsService.ts`)
- No structural changes — provider IDs come from backend
- Backend will now return `"foundry"` instead of `"azure"` in `providers[]`

**13. E2E tests**
- `azure-model-selector.spec.ts` → rename to `foundry-model-selector.spec.ts`, update mock `provider_id`
- `azure-e2e-chat.spec.ts` → rename to `foundry-e2e-chat.spec.ts`, update `provider_id: "foundry"`
- `model-picker-backend-sync.spec.ts` — update expected provider names
- `copilot-model-selector.spec.ts` — no changes needed

**14. `NavigationSettingsControls.tsx`**
- Provider display name: `"Azure AI Foundry"` instead of `"Azure OpenAI"` (if such label exists)

---

### Phase 5 — Tests *(interleaved, TDD order)*

**15. Backend tests to create / update:**

| File | Action | Coverage |
|---|---|---|
| `test_foundry_llm_provider.py` | CREATE | management-plane listing, all formats, excluded models, error handling, chat delegation |
| `test_foundry_embedding_provider.py` | CREATE | embedding discovery and delegation |
| `test_azure_secretkeeper_resolution.py` | UPDATE | `effective_foundry_*` properties |
| `test_models_service_routing.py` | UPDATE | foundry provider discovery |
| `test_settings_models_service.py` | UPDATE | `set_selection("foundry", model_id)` |
| `test_settings_router.py` | UPDATE | `/llm-options` returns `"foundry"` provider with models |
| `test_ai_service_fallback_config.py` | SIMPLIFY | remove fallback assertions |

**16. Delete obsolete test files:**
- `test_azure_openai_provider.py`
- `test_azure_openai_e2e.py`

---

### Phase 6 — Documentation *(depends on all phases)*

**17. Update existing docs:**
- `docs/backend/AI_PROVIDER_ROUTING.md` — replace Azure OpenAI with Foundry
- `docs/backend/AZURE_OPENAI_SETUP.md` → rename to `AZURE_FOUNDRY_SETUP.md`, update content
- `docs/backend/BACKEND_REFERENCE.md` — update provider references
- `docs/SYSTEM_ARCHITECTURE.md` — update architecture diagram
- `docs/README.md` — update links
- This file: mark as completed once implementation is done

---

## File Change Map

### Create
- `backend/app/shared/ai/providers/foundry_client.py`
- `backend/app/shared/ai/providers/foundry_llm.py`
- `backend/app/shared/ai/providers/foundry_embedding.py`
- `backend/tests/services/test_foundry_llm_provider.py`
- `backend/tests/services/test_foundry_embedding_provider.py`

### Modify
- `backend/app/shared/config/settings/ai.py`
- `backend/app/shared/ai/config.py`
- `backend/app/shared/config/app_settings.py`
- `backend/app/shared/ai/providers/__init__.py`
- `backend/app/shared/ai/ai_service.py`
- `backend/app/shared/ai/router.py`
- `backend/app/shared/ai/models_service.py`
- `backend/app/features/settings/application/settings_service.py`
- `frontend/src/features/settings/components/NavigationSettingsControls.tsx`
- `frontend/tests/model-picker-backend-sync.spec.ts`
- `backend/tests/core/test_azure_secretkeeper_resolution.py`
- `backend/tests/services/test_models_service_routing.py`
- `backend/tests/services/test_settings_models_service.py`
- `backend/tests/routers/test_settings_router.py`
- `backend/tests/services/test_ai_service_fallback_config.py`

### Rename
- `frontend/tests/azure-model-selector.spec.ts` → `foundry-model-selector.spec.ts`
- `frontend/tests/azure-e2e-chat.spec.ts` → `foundry-e2e-chat.spec.ts`

### Delete
- `backend/app/shared/ai/providers/azure_openai_client.py`
- `backend/app/shared/ai/providers/azure_openai_llm.py`
- `backend/app/shared/ai/providers/azure_openai_embedding.py`
- `backend/tests/services/test_azure_openai_provider.py`
- `backend/tests/services/test_azure_openai_e2e.py`

---

## Verification Checklist

```bash
# Config layer
uv run python -m pytest backend/tests/core/test_azure_secretkeeper_resolution.py

# Provider layer
uv run python -m pytest backend/tests/services/test_foundry_llm_provider.py

# Service layer
uv run python -m pytest backend/tests/services/test_models_service_routing.py
uv run python -m pytest backend/tests/services/test_settings_models_service.py
uv run python -m pytest backend/tests/routers/test_settings_router.py

# Full backend suite
uv run python -m pytest backend/tests -q

# Manual smoke test
# GET /api/settings/llm-options?refresh=true  →  11 models under "foundry"
# PUT /api/settings/llm-selection { "provider_id": "foundry", "model_id": "gpt-5.3-chat" }
# Send a chat message → response uses gpt-5.3-chat

# E2E (after frontend updates)
npx playwright test frontend/tests/foundry-model-selector.spec.ts
npx playwright test frontend/tests/foundry-e2e-chat.spec.ts
```

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Management-plane API requires Azure AD auth (not API key) | Test data-plane `/openai/deployments` first; if AIServices returns all model formats there, skip management-plane entirely |
| Non-OpenAI models fail inference despite `chatCompletion: true` | Test each model family against chat completions endpoint before shipping |
| LangChain `AzureChatOpenAI` incompatible with non-OpenAI model response format | Use `AzureChatOpenAI` only for inference; if a model requires custom parsing, wrap it |
| Tests written against `"azure"` provider id break | Update all test fixtures atomically in Phase 5; keep old tests until Phase 5 completes |
