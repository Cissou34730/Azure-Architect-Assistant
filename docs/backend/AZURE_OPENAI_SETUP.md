# Azure OpenAI Setup Guide (Step-by-Step)

This guide explains how to prepare Azure resources and configure this project to consume Azure OpenAI through the unified AI service layer.

## 1) Prerequisites

- Azure subscription with permission to create resources.
- Azure OpenAI access approved for your tenant/subscription.
- Azure CLI installed and authenticated (`az login`).
- Project backend dependencies installed (`uv sync` or `npm run installAll`).

## 2) Choose target values

Pick and record these values first:

- `SUBSCRIPTION_ID`
- `RESOURCE_GROUP` (example: `rg-aaa-ai-dev`)
- `LOCATION` (example: `swedencentral`)
- `AOAI_ACCOUNT_NAME` (example: `aoai-aaa-dev`)
- `LLM_DEPLOYMENT_NAME` (example: `gpt-4o-mini-deploy`)
- `EMBEDDING_DEPLOYMENT_NAME` (example: `text-embedding-3-small-deploy`)

## 3) Register required resource providers

Run once per subscription:

```powershell
az account set --subscription <SUBSCRIPTION_ID>
az provider register --namespace Microsoft.CognitiveServices
az provider show --namespace Microsoft.CognitiveServices --query registrationState -o tsv
```

Wait until registration state is `Registered`.

## 4) Create resource group

```powershell
az group create --name <RESOURCE_GROUP> --location <LOCATION>
```

## 5) Create Azure OpenAI account

```powershell
az cognitiveservices account create \
  --name <AOAI_ACCOUNT_NAME> \
  --resource-group <RESOURCE_GROUP> \
  --location <LOCATION> \
  --kind OpenAI \
  --sku S0 \
  --custom-domain <AOAI_ACCOUNT_NAME>
```

## 6) Create model deployments

### 6.1 LLM deployment

```powershell
az cognitiveservices account deployment create \
  --resource-group <RESOURCE_GROUP> \
  --name <AOAI_ACCOUNT_NAME> \
  --deployment-name <LLM_DEPLOYMENT_NAME> \
  --model-name gpt-4o-mini \
  --model-version "latest" \
  --model-format OpenAI
```

### 6.2 Embedding deployment

```powershell
az cognitiveservices account deployment create \
  --resource-group <RESOURCE_GROUP> \
  --name <AOAI_ACCOUNT_NAME> \
  --deployment-name <EMBEDDING_DEPLOYMENT_NAME> \
  --model-name text-embedding-3-small \
  --model-version "latest" \
  --model-format OpenAI
```

### 6.3 Verify deployments

```powershell
az cognitiveservices account deployment list \
  --resource-group <RESOURCE_GROUP> \
  --name <AOAI_ACCOUNT_NAME> \
  --query "[].{deployment:name,model:properties.model.name,version:properties.model.version}" \
  -o table
```

## 7) Collect endpoint and key

```powershell
az cognitiveservices account show \
  --name <AOAI_ACCOUNT_NAME> \
  --resource-group <RESOURCE_GROUP> \
  --query properties.endpoint -o tsv

az cognitiveservices account keys list \
  --name <AOAI_ACCOUNT_NAME> \
  --resource-group <RESOURCE_GROUP> \
  --query key1 -o tsv
```

Save the returned values as:

- `AZURE_OPENAI_ENDPOINT` (for `AI_AZURE_OPENAI_ENDPOINT`)
- `AZURE_OPENAI_API_KEY` (store in SecretKeeper as `AI_AZURE_OPENAI_API_KEY`)

## 8) Configure project environment variables

The project AI layer uses `AI_`-prefixed variables (`backend/app/services/ai/config.py`).

Update your local `.env` with one of the configurations below.

Store secret keys in SecretKeeper before starting the backend:

```powershell
sk set AI_OPENAI_API_KEY "<OPENAI_API_KEY>"
sk set AI_AZURE_OPENAI_API_KEY "<AZURE_OPENAI_API_KEY>"
```

All Azure configuration can be stored in SecretKeeper (recommended):

```powershell
sk set AI_AZURE_OPENAI_ENDPOINT "https://<AOAI_ACCOUNT_NAME>.openai.azure.com/"
sk set AI_AZURE_LLM_DEPLOYMENT "<LLM_DEPLOYMENT_NAME>"
sk set AI_AZURE_LLM_DEPLOYMENTS "<LLM_DEPLOYMENT_NAME>"
sk set AI_AZURE_EMBEDDING_DEPLOYMENT "<EMBEDDING_DEPLOYMENT_NAME>"
```

Each Azure setting is resolved through `effective_` properties in `AppSettings`:
SecretKeeper → environment variable → empty string.
Only non-secret or provider-level settings need to stay in `.env`.

### Option A: Azure as primary provider

```dotenv
AI_LLM_PROVIDER=azure
AI_EMBEDDING_PROVIDER=azure
AI_FALLBACK_ENABLED=false
AI_FALLBACK_PROVIDER=none
AI_FALLBACK_ON_TRANSIENT_ONLY=true

AI_AZURE_OPENAI_ENDPOINT=https://<AOAI_ACCOUNT_NAME>.openai.azure.com/
AI_AZURE_OPENAI_API_VERSION=2024-02-15-preview
AI_AZURE_LLM_DEPLOYMENT=<LLM_DEPLOYMENT_NAME>
AI_AZURE_EMBEDDING_DEPLOYMENT=<EMBEDDING_DEPLOYMENT_NAME>

# Optional: comma-separated deployment list for model-list metadata endpoint
AI_AZURE_LLM_DEPLOYMENTS=<LLM_DEPLOYMENT_NAME>
```

### Option B: OpenAI primary with Azure fallback

```dotenv
AI_LLM_PROVIDER=openai
AI_EMBEDDING_PROVIDER=openai
AI_FALLBACK_ENABLED=true
AI_FALLBACK_PROVIDER=azure
AI_FALLBACK_ON_TRANSIENT_ONLY=true

AI_OPENAI_LLM_MODEL=gpt-4o-mini
AI_OPENAI_EMBEDDING_MODEL=text-embedding-3-small

AI_AZURE_OPENAI_ENDPOINT=https://<AOAI_ACCOUNT_NAME>.openai.azure.com/
AI_AZURE_OPENAI_API_VERSION=2024-02-15-preview
AI_AZURE_LLM_DEPLOYMENT=<LLM_DEPLOYMENT_NAME>
AI_AZURE_EMBEDDING_DEPLOYMENT=<EMBEDDING_DEPLOYMENT_NAME>
AI_AZURE_LLM_DEPLOYMENTS=<LLM_DEPLOYMENT_NAME>
```

## 9) Start backend and validate runtime wiring

Start backend:

```powershell
npm run backend
```

Validate models endpoint:

- `GET /api/settings/available-models`
- `GET /api/settings/current-model`

Expected behavior:

- Azure primary: the backend calls `GET /openai/models?api-version=2024-10-21` on the Azure resource to discover all available base models; the UI dropdown shows inference-capable LLMs, including GPT-5.x and Codex families, while embedding, image, audio, realtime, and router models are filtered out. Configured deployments are always merged into the dropdown first so working deployment IDs such as `aaadp` remain selectable even when the catalog returns base model names. Falls back to configured deployment names on API failure.
- OpenAI primary + Azure fallback: OpenAI is attempted first; fallback only on transient failures.
- Agent startup and health checks validate the selected AI provider configuration, so Azure-only deployments no longer depend on an OpenAI-specific readiness check.
- KB creation defaults, ingestion embedding, and LlamaIndex adapter wiring follow the active provider configuration rather than assuming OpenAI model names.

> **Note:** Model discovery uses the Azure OpenAI data-plane
> `GET /openai/models?api-version=2024-10-21` endpoint which lists all base
> models available on the resource. Results are cached for 7 days. The
> selector keeps configured deployments and filters the catalog down to
> inference-capable LLMs rather than requiring `chat_completion`, which allows
> Codex deployments and GPT-5 Codex variants to appear alongside chat models.

## 10) Fallback validation (manual)

1. Configure Option B (OpenAI primary + Azure fallback).
2. Trigger a transient OpenAI failure (timeout/429/5xx scenario).
3. Send an inference request through normal application flow.
4. Confirm request succeeds via Azure deployment.
5. Trigger a non-transient failure and confirm no fallback occurs.

## 11) Common troubleshooting

### `ValueError` about missing Azure fields

The AI config validator requires Azure endpoint/key/deployments whenever Azure is selected as primary or fallback.

### 404/Deployment not found

- Deployment name in `.env` must match Azure deployment name exactly.
- Ensure deployment exists in the same Azure OpenAI account as the endpoint.

### 401/403 authentication errors

- Rotate/regenerate key and update `AI_AZURE_OPENAI_API_KEY` in SecretKeeper (`sk set AI_AZURE_OPENAI_API_KEY ...`).
- Verify subscription/resource access and account firewall restrictions.

### Wrong endpoint format

Use account endpoint format like:

`https://<account-name>.openai.azure.com/`

### Models endpoint returns empty for Azure

Set at least:

- `AI_AZURE_LLM_DEPLOYMENT`

Optionally add:

- `AI_AZURE_LLM_DEPLOYMENTS` (comma-separated)

### GPT-5 or Codex models do not appear in the selector

- Refresh `GET /api/settings/llm-options?refresh=true` after switching to the Azure provider.
- Verify the Azure resource returns the expected catalog entries from `GET /openai/models?api-version=2024-10-21`.
- Keep `AI_AZURE_LLM_DEPLOYMENT` set to a known working deployment ID so the selector still includes a deployable model even if the catalog changes.
- If the UI lists base model IDs but chat fails with 404, select the configured deployment ID instead of the base catalog model.

## 12) Related docs

- `docs/backend/AI_PROVIDER_ROUTING.md`
- `docs/backend/BACKEND_REFERENCE.md`
- `docs/operations/DEVELOPMENT_GUIDE.md`
