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

## Configuration

All fields use the `AI_` env prefix (Pydantic settings):

- `AI_LLM_PROVIDER` (`openai`, `azure`, `anthropic`, `local`)
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

### SecretKeeper Notes

- The backend resolves `AI_OPENAI_API_KEY` and `AI_AZURE_OPENAI_API_KEY` from SecretKeeper first.
- Resolution is centralized in `AppSettings` (`effective_openai_api_key`, `effective_azure_openai_api_key`) and consumed by AI runtime config.
- If a key is not present in SecretKeeper, runtime falls back to existing environment values for compatibility.
- Ensure vault is unlocked before startup: `sk unlock`.

## Validation Rules

`AIConfig.validate_provider_config()` requires credentials/deployments conditionally:

- OpenAI key is required when OpenAI is primary **or** fallback
- Azure endpoint/key/LLM deployment required when Azure is LLM primary **or** fallback
- Azure endpoint/key/embedding deployment required when Azure is embedding primary **or** fallback

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

- OpenAI primary: list via OpenAI API with disk cache
- Azure primary: list from configured deployment metadata (`AI_AZURE_LLM_DEPLOYMENT`, `AI_AZURE_LLM_DEPLOYMENTS`)
- OpenAI primary + Azure fallback: if OpenAI model listing fails, return Azure deployment metadata list

This avoids dependence on Azure OpenAI model listing semantics.

## LangGraph Path

`backend/app/agents_system/langgraph/nodes/agent_native.py` now builds its chat LLM through `AIService.create_chat_llm()` instead of constructing `ChatOpenAI` directly.

This keeps provider selection in one place and aligns runtime wiring with AI service configuration.

## Setup Runbook

For full Azure resource provisioning and project configuration steps, see:

- `docs/backend/AZURE_OPENAI_SETUP.md`
