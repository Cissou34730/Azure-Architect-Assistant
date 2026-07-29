# AI Provider Routing

## Overview

The backend AI abstraction routes through a primary provider with an optional cross-provider fallback chain for transient faults.

Application code uses `AIService` as the public entry point for:

- `chat`
- `complete`
- `embed_text`
- `embed_batch`
- provider-selected LangGraph chat adapter creation

## Resilience

### Transient-fault retry

Non-streaming LLM calls are wrapped in an explicit application-level retry (`app/shared/ai/transient_retry.py`). The OpenAI SDK itself runs with `max_retries=0` so the retry policy is fully controlled by the backend.

- Retryable faults: rate limits (429), timeouts, connection errors, and 5xx / 408 / 409 / 425 status codes.
- Policy: exponential backoff with jitter, `AI_TRANSIENT_MAX_ATTEMPTS` attempts (default 3, env `AI_TRANSIENT_MAX_ATTEMPTS`).
- Non-transient errors (auth failures, bad requests) are re-raised immediately.

### Cross-provider fallback

`AIRouter` accepts an ordered list of fallback provider factories. When the primary LLM fails with a *transient* error, the router lazily instantiates the next configured fallback and retries the call there.

- Configured via `AI_LLM_FALLBACK_PROVIDERS` (comma-separated provider names, e.g. `foundry,openai`).
- Only providers with valid credentials configured are used; unconfigured entries are skipped.
- Fallback applies to `chat` and `complete`; streaming calls and embeddings do **not** fall back.
- Fallback providers are instantiated lazily and cached; a broken fallback is skipped for the rest of the process.

## Supported providers

- `openai`
- `foundry`
- `copilot`

`foundry` is the Azure-hosted provider ID used for Azure AI Foundry / AIServices deployments. The legacy runtime provider id `azure` is rejected and callers must switch to `foundry`.

## Configuration

All fields use the `AI_` env prefix and are read through `AppSettings`.

### OpenAI

- `AI_OPENAI_API_KEY` (SecretKeeper-first)
- `AI_OPENAI_LLM_MODEL`
- `AI_OPENAI_EMBEDDING_MODEL`
- `AI_OPENAI_TIMEOUT`
- `AI_OPENAI_MAX_RETRIES`

### Azure AI Foundry

- `AI_FOUNDRY_ENDPOINT`
- `AI_FOUNDRY_API_KEY` (SecretKeeper-first)
- inference uses the Microsoft Foundry/OpenAI v1 base URL and does not require a runtime `api-version`
- `AI_FOUNDRY_RESOURCE_ID`

There is no static Foundry deployment env var. The active Foundry deployment is selected through the settings API and persisted at runtime.

### GitHub Copilot

- `AI_COPILOT_TOKEN` (SecretKeeper-first; falls back to the `GITHUB_TOKEN` env var through the `github_token` settings field)
- `AI_COPILOT_DEFAULT_MODEL`
- `AI_COPILOT_ALLOWED_MODELS`
- `AI_COPILOT_REQUEST_TIMEOUT`
- `AI_COPILOT_STARTUP_TIMEOUT`
- `AI_COPILOT_AUTH_POLL_INTERVAL`
- `AI_COPILOT_AUTH_TIMEOUT`

## Runtime selection persistence

Provider/model changes made through `PUT /api/settings/llm-selection` are persisted to `DATA_ROOT/runtime_ai_selection.json`.

- `AppSettings` reapplies the saved provider/model before `AIConfig.default()` is built.
- `AIServiceManager.reinitialize_with_selection(...)` switches the live singleton immediately.
- Saved selections support `openai`, `foundry`, and `copilot`.

## SecretKeeper resolution

The migrated runtime resolves secrets centrally through `AppSettings`:

- `effective_openai_api_key`
- `effective_foundry_endpoint`
- `effective_foundry_api_key`
- `effective_foundry_resource_id`
- `effective_copilot_token`

Resolution order is SecretKeeper first, then env/config values, then empty string where applicable.

## Validation rules

`AIConfig.validate_provider_config()` currently enforces:

- OpenAI key when OpenAI is the active LLM or embedding provider
- Foundry endpoint + API key + resource id + runtime model when Foundry is the active LLM provider
- Foundry endpoint + API key + resource id when Foundry is the active embedding provider
- Copilot default model when Copilot is the active LLM provider

## Model listing strategy

`ModelsService` uses provider-backed runtime discovery with disk caching:

- OpenAI: `AIService.list_llm_runtime_models()`
- Foundry: `FoundryLLMProvider.list_runtime_models()`
- Copilot: `CopilotLLMProvider.list_runtime_models()`

For Foundry, deployment discovery uses the Cognitive Services management-plane endpoint first and falls back to the data-plane `/openai/deployments` endpoint when management-plane API-key auth is rejected.

## LangGraph path

`backend/app/agents_system/langgraph/nodes/agent_native.py` builds its chat LLM through `AIService.create_chat_llm()`.

For Foundry, `AIService.create_chat_llm()` uses `langchain_openai.ChatOpenAI` with the Microsoft Foundry/OpenAI v1 base URL:

- `base_url=<foundry endpoint>/openai/v1/`
- `api_key=config.foundry_api_key`
- `model=config.foundry_model`

## KB and ingestion defaults

Provider-neutral defaults continue to resolve from the active AI configuration:

- KB defaults use the active LLM and embedding identities
- ingestion embedding defaults follow the active embedding identity
- vector/index metadata uses the active runtime model identity

## Setup runbook

For Azure AI Foundry setup and runtime activation steps, see:

- `docs/backend/AZURE_FOUNDRY_SETUP.md`
