"""E2E smoke test for Azure OpenAI chat and embedding.

Run with Azure env vars set:
  uv run python -m pytest backend/tests/services/test_azure_openai_e2e.py -v

Requires real Azure OpenAI access. Skipped when env vars are missing.
"""
import os

import pytest

from app.shared.ai.ai_service import AIService
from app.shared.ai.config import AIConfig
from app.shared.ai.interfaces import ChatMessage
from app.shared.ai.providers.azure_openai_client import reset_azure_openai_client
from app.shared.ai.providers.azure_openai_embedding import AzureOpenAIEmbeddingProvider
from app.shared.ai.providers.azure_openai_llm import AzureOpenAILLMProvider

# Skip entire module if Azure config is missing
pytestmark = pytest.mark.skipif(
    not os.environ.get("AI_AZURE_OPENAI_ENDPOINT"),
    reason="AI_AZURE_OPENAI_ENDPOINT not set; skipping Azure E2E tests",
)


def _real_azure_config() -> AIConfig:
    return AIConfig(
        llm_provider="azure",
        embedding_provider="azure",
        azure_openai_endpoint=os.environ.get("AI_AZURE_OPENAI_ENDPOINT", ""),
        azure_openai_api_key=os.environ.get("AI_AZURE_OPENAI_API_KEY", ""),
        azure_openai_api_version=os.environ.get("AI_AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_llm_deployment=os.environ.get("AI_AZURE_LLM_DEPLOYMENT", ""),
        azure_llm_deployments=os.environ.get("AI_AZURE_LLM_DEPLOYMENTS", ""),
        azure_embedding_deployment=os.environ.get("AI_AZURE_EMBEDDING_DEPLOYMENT", ""),
        openai_embedding_model="text-embedding-3-small",
    )


@pytest.mark.asyncio
async def test_azure_chat_completion() -> None:
    """Verify Azure OpenAI chat completion works end-to-end."""
    reset_azure_openai_client()  # ensure fresh client
    config = _real_azure_config()
    provider = AzureOpenAILLMProvider(config)

    result = await provider.chat(
        messages=[ChatMessage(role="user", content="Reply with exactly: hello azure")],
        temperature=0.0,
        max_tokens=50,
    )

    assert result.content is not None
    assert len(result.content) > 0
    assert "hello" in result.content.lower() or "azure" in result.content.lower()
    assert result.usage is not None


@pytest.mark.asyncio
async def test_azure_embedding() -> None:
    """Verify Azure OpenAI embedding works end-to-end."""
    reset_azure_openai_client()  # ensure fresh client
    config = _real_azure_config()
    provider = AzureOpenAIEmbeddingProvider(config)

    result = await provider.embed_text("Hello, world!")

    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(v, float) for v in result)


@pytest.mark.asyncio
async def test_azure_embedding_batch() -> None:
    """Verify Azure OpenAI batch embedding works end-to-end."""
    reset_azure_openai_client()
    config = _real_azure_config()
    provider = AzureOpenAIEmbeddingProvider(config)

    result = await provider.embed_batch(["Hello", "World"], batch_size=2)

    assert len(result) == 2
    assert all(isinstance(v, list) for v in result)


@pytest.mark.asyncio
async def test_azure_list_deployments() -> None:
    """Verify Azure OpenAI deployment listing works end-to-end."""
    reset_azure_openai_client()
    config = _real_azure_config()
    provider = AzureOpenAILLMProvider(config)

    result = await provider.list_runtime_models()

    assert isinstance(result, list)
    assert len(result) >= 1
    deployment_ids = [entry["id"] for entry in result]
    assert "aaadp" in deployment_ids


@pytest.mark.asyncio
async def test_azure_create_chat_llm() -> None:
    """Verify AzureChatOpenAI LangChain adapter works end-to-end."""
    reset_azure_openai_client()
    config = _real_azure_config()
    service = AIService(config)

    chat_llm = service.create_chat_llm(temperature=0.0)

    response = await chat_llm.ainvoke("Reply with exactly: pong")

    assert response.content is not None
    assert len(response.content) > 0

