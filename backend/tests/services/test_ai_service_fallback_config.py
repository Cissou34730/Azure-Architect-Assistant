import pytest

from app.services.ai.ai_service import AIService
from app.services.ai.config import AIConfig
from app.services.ai.providers import AzureOpenAIEmbeddingProvider, AzureOpenAILLMProvider


def _base_openai_config() -> dict:
    return {
        "openai_api_key": "test-openai-key",
        "openai_llm_model": "gpt-4o-mini",
        "openai_embedding_model": "text-embedding-3-small",
    }


def _azure_fields() -> dict:
    return {
        "azure_openai_endpoint": "https://example.openai.azure.com",
        "azure_openai_api_key": "test-azure-key",
        "azure_llm_deployment": "gpt-4o-mini-deployment",
        "azure_embedding_deployment": "text-embedding-deployment",
    }


def test_validate_requires_azure_fields_when_azure_is_fallback() -> None:
    config = AIConfig(
        **_base_openai_config(),
        fallback_enabled=True,
        fallback_provider="azure",
        llm_provider="openai",
        embedding_provider="openai",
    )

    with pytest.raises(ValueError, match="Azure endpoint, API key"):
        config.validate_provider_config()


def test_validate_requires_openai_key_when_openai_is_fallback() -> None:
    config = AIConfig(
        **_azure_fields(),
        fallback_enabled=True,
        fallback_provider="openai",
        llm_provider="azure",
        embedding_provider="azure",
    )

    with pytest.raises(ValueError, match="OpenAI API key"):
        config.validate_provider_config()


def test_ai_service_builds_azure_fallback_providers() -> None:
    config = AIConfig(
        **_base_openai_config(),
        **_azure_fields(),
        llm_provider="openai",
        embedding_provider="openai",
        fallback_enabled=True,
        fallback_provider="azure",
    )

    service = AIService(config)

    assert isinstance(service._fallback_llm_provider, AzureOpenAILLMProvider)
    assert isinstance(service._fallback_embedding_provider, AzureOpenAIEmbeddingProvider)
