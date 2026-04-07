# GitHub Copilot Integration Setup

## Prerequisites

1. A GitHub account with active Copilot subscription.
2. A GitHub **Personal Access Token (PAT)** with the `copilot` scope.
3. Install dependencies with `uv sync`.

## Configuration

1. Set `AI_LLM_PROVIDER=copilot`.
2. Set `AI_COPILOT_TOKEN` to your GitHub PAT (or set `GITHUB_TOKEN` as a fallback).
3. Optionally set `AI_COPILOT_DEFAULT_MODEL` (default: `gpt-4.1`) and `AI_COPILOT_ALLOWED_MODELS`.
4. Keep `AI_EMBEDDING_PROVIDER` on `openai` or `azure` (Copilot does not support embeddings).

### Authentication

Token resolution order (via `AppSettings.effective_copilot_token`):
1. SecretKeeper vault key `ai_copilot_token`
2. `AI_COPILOT_TOKEN` environment variable
3. `GITHUB_TOKEN` environment variable

The **Copilot SDK** (`github-copilot-sdk`) handles all Copilot interactions:
- **Model discovery**: `CopilotRuntime.list_models()` returns subscription-scoped models via the SDK. Only models the user actually has access to are listed.
- **Inference**: `CopilotRuntime.send_message()` sends chat completions through the SDK (uses `api.githubcopilot.com` internally with SDK-managed session tokens).
- **Auth status**: Login/logout flows and status display.

The **LangChain path** (`CopilotChatModel`) wraps the SDK for use with LangGraph agent pipelines. `AIService.create_chat_llm()` returns a `CopilotChatModel` instance — a custom `BaseChatModel` subclass that delegates inference to `CopilotRuntime.send_message()` and `stream_message()`. Tool calling is prompt-based: tool schemas are injected into the system message and `<tool_call>` XML blocks are parsed from the response, keeping full compatibility with `bind_tools()`, `ToolNode`, and the LangGraph agent loop.

If the SDK is unreachable, model discovery falls back to the configured `AI_COPILOT_ALLOWED_MODELS` allowlist.

When Copilot is selected from the backend settings UI, that provider/model choice is persisted under `DATA_ROOT/runtime_ai_selection.json` so agent traffic continues to use Copilot after a backend restart.

## Architecture

The Copilot integration uses the SDK for both discovery and inference:

- **`CopilotChatModel`** (`BaseChatModel`): `AIService.create_chat_llm()` returns this custom LangChain chat model. It delegates to `CopilotRuntime.send_message()` for inference and supports prompt-based tool calling via `<tool_call>` XML blocks. This enables all SDK models (including Claude and codex) to work with `bind_tools()`, `ToolNode`, and the LangGraph agent loop.
- **`CopilotRuntime`** (via `github-copilot-sdk`): Manages the shared `CopilotClient` singleton for model discovery (`list_models()`), chat inference (`send_message()`/`stream_message()`), and authentication status.
- **`CopilotLLMProvider`**: Non-LangChain path implementing the `LLMProvider` interface. Uses SDK for both model discovery and chat/complete operations.

## Available Models

The SDK returns subscription-scoped models — only models the user has access to. Typical models include:
- OpenAI: `gpt-4.1`, `gpt-5-mini`, `gpt-5.1`, `gpt-5.2`, `gpt-5.1-codex`, `gpt-5.2-codex`, `gpt-5.3-codex`
- Anthropic: `claude-sonnet-4.6`, `claude-sonnet-4.5`, `claude-opus-4.6`, `claude-opus-4.5`, `claude-haiku-4.5`

Model IDs are SDK-native names (e.g. `gpt-5.2`, `claude-sonnet-4.6`) — **not** publisher-prefixed catalog IDs.

Embedding models are not included — embeddings go through OpenAI/Azure.

## Notes

- SDK model IDs (e.g. `gpt-5.2`, `claude-sonnet-4.6`) are distinct from GitHub Models catalog IDs (e.g. `openai/gpt-4o-mini`). Most SDK models do **not** have a matching catalog entry.
- The `api.githubcopilot.com` endpoint does **not** accept PATs — only SDK-managed session tokens. All inference goes through the SDK.
- Tool calling for SDK models uses prompt-based injection (`<tool_call>` XML blocks) rather than native OpenAI function calling. This works reliably with Claude and GPT models.
- Copilot cannot be used as a fallback provider or embedding provider.
- Temperature, max_tokens, and timeout are fully configurable via environment variables.
