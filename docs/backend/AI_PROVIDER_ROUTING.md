# AI Provider Routing (OpenAI Primary, Azure Fallback)

## Overview

The backend AI abstraction (`app/services/ai`) now supports a single runtime call path with optional failover:

- Primary provider from `AIConfig.llm_provider` / `AIConfig.embedding_provider`
- Optional fallback provider from `AIConfig.fallback_provider`
- Fallback gate from `AIConfig.fallback_enabled`
- Fallback policy from `AIConfig.fallback_on_transient_only`

Application code still uses `AIService` as the only public entry point for:

- `chat`
- `complete`
- `embed_text`
- `embed_batch`
- provider-selected LangGraph chat adapter creation

## Configuration

All fields use the `AI_` env prefix (Pydantic settings):

- `AI_LLM_PROVIDER` (`openai`, `azure`, `anthropic`, `local`, `copilot`)
- `AI_EMBEDDING_PROVIDER` (`openai`, `azure`, `local`)
- `AI_FALLBACK_PROVIDER` (`openai`, `azure`, `none`)
- `AI_FALLBACK_ENABLED` (`true`/`false`)
- `AI_FALLBACK_ON_TRANSIENT_ONLY` (`true`/`false`)

OpenAI fields:

- `AI_OPENAI_API_KEY` (SecretKeeper vault key; not stored in `.env`)
- `AI_OPENAI_LLM_MODEL`
- `AI_OPENAI_EMBEDDING_MODEL`
- `AI_OPENAI_TIMEOUT`
- `AI_OPENAI_MAX_RETRIES`

Azure OpenAI fields:

- `AI_AZURE_OPENAI_ENDPOINT`
- `AI_AZURE_OPENAI_API_KEY` (SecretKeeper vault key; not stored in `.env`)
- `AI_AZURE_OPENAI_API_VERSION`
- `AI_AZURE_LLM_DEPLOYMENT`
- `AI_AZURE_LLM_DEPLOYMENTS` (optional comma-separated list for model-list endpoint metadata)
- `AI_AZURE_EMBEDDING_DEPLOYMENT`

GitHub Copilot fields:

- `AI_COPILOT_TOKEN` (GitHub PAT with `copilot` scope; or `GITHUB_TOKEN` as fallback)
- `AI_COPILOT_DEFAULT_MODEL`
- `AI_COPILOT_ALLOWED_MODELS`
- `AI_COPILOT_REQUEST_TIMEOUT`
- `AI_COPILOT_STARTUP_TIMEOUT`
- `AI_COPILOT_AUTH_POLL_INTERVAL`
- `AI_COPILOT_AUTH_TIMEOUT`

> **Note:** The Copilot LangChain path uses the GitHub Models API (`https://models.github.ai/inference`)
> with a GitHub PAT as the API key. This provides full `ChatOpenAI` compatibility including
> native tool calling, streaming, and temperature/max_tokens support.
> Model discovery uses the Copilot SDK (`CopilotRuntime.list_models()`) which returns
> subscription-scoped models with SDK-native IDs (e.g. `gpt-5.2`, `claude-sonnet-4.6`).
> Model discovery uses the GitHub Models catalog API (`https://models.github.ai/catalog/models`)
> with `X-GitHub-Api-Version: 2026-03-10` header. Model IDs use the full `{publisher}/{model-name}` format
> (e.g. `openai/gpt-4o-mini`) as required by the official inference endpoint.

### Runtime Selection Persistence

Provider/model changes made through the settings API are persisted to `DATA_ROOT/runtime_ai_selection.json`.

- The live `AIService` singleton is still reinitialized immediately.
- On the next backend startup, `AppSettings` re-applies the persisted provider/model override before `AIConfig.default()` is built.
- This keeps LangGraph native agent execution aligned with the last UI-selected provider instead of falling back to the env default after restart.

### SecretKeeper Notes

- The backend resolves `AI_OPENAI_API_KEY` and `AI_AZURE_OPENAI_API_KEY` from SecretKeeper first.
- Resolution is centralized in `AppSettings` (`effective_openai_api_key`, `effective_azure_openai_api_key`) and consumed by AI runtime config.
- If a key is not present in SecretKeeper, runtime falls back to existing environment values for compatibility.
- Ensure vault is unlocked before startup: `sk unlock`.

## Validation Rules

`AIConfig.validate_provider_config()` requires credentials/deployments conditionally:

- OpenAI key is required when OpenAI is primary **or** fallback
- Azure endpoint/key/LLM deployment required when Azure is LLM primary **or** fallback
- Azure endpoint/key/embedding deployment required when Azure is the *primary* embedding provider (embedding fallback is disabled — different providers produce incompatible vector dimensions)
- Copilot default model required when Copilot is selected as the LLM provider; authentication is handled by the Copilot SDK via CLI login (no token required at startup)

## Fallback Behavior

Fallback is attempted only when all are true:

1. `AI_FALLBACK_ENABLED=true`
2. fallback provider exists and differs from primary
3. error matches policy

With `AI_FALLBACK_ON_TRANSIENT_ONLY=true`, fallback triggers for transient failures only:

- timeouts
- rate limits
- retriable API errors (`429`, `5xx`)

Non-transient failures are re-raised from primary.

For streaming, fallback is only attempted before the first token is emitted.

## Model Listing Strategy

`ModelsService` behavior:

- OpenAI primary: list via `AIService.list_llm_runtime_models()` with disk cache
- Azure primary: list via `AIService.list_llm_runtime_models()` using configured Azure deployment ids only (`AI_AZURE_LLM_DEPLOYMENT` plus optional `AI_AZURE_LLM_DEPLOYMENTS`)
- Copilot primary: `CopilotLLMProvider.list_runtime_models()` queries the Copilot SDK (`CopilotRuntime.list_models()`) returning subscription-scoped models. Only models the user actually has access to (including Claude, codex, and GPT-5.x exclusives) are listed. Falls back to the configured `AI_COPILOT_ALLOWED_MODELS` allowlist on failure.
- OpenAI primary + Azure fallback: if OpenAI model listing fails, query Azure via provider-backed runtime listing

`ModelsService` no longer imports provider SDK clients directly for listing. The model/deployment discovery path now flows through the centralized AI service/provider abstraction.

## LangGraph Path

`backend/app/agents_system/langgraph/nodes/agent_native.py` now builds its chat LLM through `AIService.create_chat_llm()` instead of constructing provider clients directly inside the LangGraph node.

This keeps provider selection in one place and aligns runtime wiring with AI service configuration.

At this stage, the native LangGraph tool-binding path centralizes provider selection and credentials in `AIService`, but fallback behavior still applies only to the `AIService.chat` / `complete` / `embed_*` call path until native failover is implemented.

## KB And Ingestion Defaults

Provider-neutral defaults now resolve from the active AI configuration rather than from OpenAI-only settings names:

- KB config defaults use the active LLM and embedding identities
- KB management request defaults use the active embedding identity
- ingestion pipeline components default to the active embedding identity
- the active ingestion embedder delegates to `AIService.embed_text()` rather than constructing `OpenAIEmbedding` directly
- LlamaIndex adapters and vector indexing metadata use the active runtime model or deployment names

## Setup Runbook

For full Azure resource provisioning and project configuration steps, see:

- `docs/backend/AZURE_OPENAI_SETUP.md`
