# Azure OpenAI Credentials Reference

> **SECURITY WARNING**: Move this file to a secure location and delete from repo.
> The API key is stored in SecretKeeper as `AI_AZURE_OPENAI_API_KEY`.

## Resource Details

- **Subscription**: `a32f5058-d24d-4a60-8b2b-c617321d8ca0`
- **Resource Group**: `AAA`
- **Account Name**: `aaaoi`
- **Location**: `francecentral`

## Endpoint

```
https://aaaoi.openai.azure.com/
```

## API Key (key1)

```

```

## Deployments

| Deployment | Model | Version | SKU |
|---|---|---|---|
| `aaadp` | gpt-4o-mini | 2024-07-18 | GlobalStandard (50) |
| `text-embedding-3-small` | text-embedding-3-small | 1 | GlobalStandard (50) |

## Environment Variables

```dotenv
AI_AZURE_OPENAI_ENDPOINT=https://aaaoi.openai.azure.com/
AI_AZURE_OPENAI_API_VERSION=2024-02-15-preview
AI_AZURE_LLM_DEPLOYMENT=aaadp
AI_AZURE_LLM_DEPLOYMENTS=aaadp
AI_AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

## SecretKeeper

```powershell
sk set AI_AZURE_OPENAI_API_KEY "<redacted-secretkeeper-value>"
```
