# Azure AI Foundry Setup Guide

This guide explains how to configure the migrated `foundry` provider used by the backend AI service layer.

## 1) Prerequisites

- Azure subscription with access to an AIServices account
- Azure CLI authenticated with `az login`
- SecretKeeper available locally (`sk`)
- Backend dependencies installed with `uv`

## 2) Required Foundry values

Record these values for the target AIServices account:

- `AI_FOUNDRY_ENDPOINT`
- `AI_FOUNDRY_API_KEY`
- `AI_FOUNDRY_RESOURCE_ID`
- optional `AI_FOUNDRY_API_VERSION` override (defaults to `2024-10-21`)

Example endpoint shape:

`https://<account-name>.cognitiveservices.azure.com/`

Example resource id shape:

`/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account-name>`

## 3) Store Foundry secrets in SecretKeeper

```powershell
sk set AI_FOUNDRY_ENDPOINT "https://<account-name>.cognitiveservices.azure.com/"
sk set AI_FOUNDRY_API_KEY "<api-key>"
sk set AI_FOUNDRY_RESOURCE_ID "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account-name>"
```

OpenAI and Copilot can still be configured independently if you use those providers:

```powershell
sk set AI_OPENAI_API_KEY "<openai-key>"
sk set AI_COPILOT_TOKEN "<github-token>"
```

## 4) Provider defaults

The migrated runtime supports these provider ids:

- `openai`
- `foundry`
- `copilot`

Use `AI_LLM_PROVIDER=foundry` and `AI_EMBEDDING_PROVIDER=foundry` when you want Foundry to be the configured default provider.

## 5) Start the backend

```powershell
npm run backend
```

## 6) Discover and activate a Foundry deployment

Foundry no longer uses a static deployment env var. Instead:

1. Refresh the provider model list
2. Pick a deployment id returned by the backend
3. Persist it through the settings API

Example flow:

```powershell
Invoke-RestMethod http://localhost:8000/api/settings/llm-options?refresh=true

Invoke-RestMethod `
  -Method Put `
  -Uri http://localhost:8000/api/settings/llm-selection `
  -ContentType "application/json" `
  -Body '{"provider_id":"foundry","model_id":"gpt-5.3-chat"}'
```

That selection is persisted to `backend/data/runtime_ai_selection.json` and reused on the next startup.

## 7) Expected runtime behavior

- `GET /api/settings/llm-options?refresh=true` returns Foundry deployments under provider id `foundry`
- `PUT /api/settings/llm-selection` with `provider_id="foundry"` activates the selected deployment
- `AIService.create_chat_llm()` uses `AzureChatOpenAI` against the Foundry endpoint with the selected deployment id
- embedding calls use the Foundry endpoint and auto-select an embedding deployment when needed

## 8) Discovery behavior

Foundry deployment discovery uses:

1. Cognitive Services management-plane deployment listing
2. data-plane `/openai/deployments` fallback (pinned to `api-version=2023-03-15-preview`, the only version accepted by the listing endpoint) when management-plane API-key auth is rejected

The backend filters out non-chat deployments for runtime LLM selection and keeps embedding discovery separate.

## 9) Troubleshooting

### `Foundry endpoint, API key, resource id, and runtime model required`

The provider is configured as `foundry`, but one of these is still missing:

- `AI_FOUNDRY_ENDPOINT`
- `AI_FOUNDRY_API_KEY`
- `AI_FOUNDRY_RESOURCE_ID`
- a saved runtime model selection

### `Provider 'azure' is no longer supported. Use 'foundry'.`

A caller is still sending the legacy provider id. Update the request payload to `foundry`.

### No Foundry models appear after refresh

- Verify the endpoint/key/resource id belong to the same AIServices account
- Confirm the account has successful deployments
- Retry with `GET /api/settings/llm-options?refresh=true`

### Management-plane discovery returns 401

This is expected for some API-key-only setups. The backend falls back to the data-plane deployment listing automatically.

## Related docs

- `docs/backend/AI_PROVIDER_ROUTING.md`
- `docs/backend/BACKEND_REFERENCE.md`
- `docs/architecture/system-architecture.md`
