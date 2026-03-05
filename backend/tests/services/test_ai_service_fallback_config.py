import pytest

import app.core.app_settings as app_settings_module
from app.core.app_settings import AppSettings
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


def test_app_settings_effective_keys_prefer_secretkeeper(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "AI_OPENAI_API_KEY": "sk-openai-key",
        "AI_AZURE_OPENAI_API_KEY": "sk-azure-key",
    }
    monkeypatch.setattr("app.core.app_settings._read_secretkeeper_secret", lambda key: values.get(key))

    settings = AppSettings(
        ai_openai_api_key="env-openai-key",
        ai_azure_openai_api_key="env-azure-key",
        openai_api_key="legacy-openai-key",
    )

    assert settings.effective_openai_api_key == "sk-openai-key"
    assert settings.effective_azure_openai_api_key == "sk-azure-key"


def test_app_settings_effective_keys_fall_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.app_settings._read_secretkeeper_secret", lambda _key: None)

    settings = AppSettings(
        ai_openai_api_key="",
        ai_azure_openai_api_key="env-azure-key",
        openai_api_key="legacy-openai-key",
    )

    assert settings.effective_openai_api_key == "legacy-openai-key"
    assert settings.effective_azure_openai_api_key == "env-azure-key"


def test_app_settings_effective_openai_key_empty_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.core.app_settings._read_secretkeeper_secret", lambda _key: None)

    settings = AppSettings(ai_openai_api_key="", openai_api_key=None)

    assert settings.effective_openai_api_key == ""


def test_read_secretkeeper_secret_returns_none_for_expected_runtime_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class VaultLockedError(Exception):
        pass

    class _LockedClient:
        def get_or_none(self, _key: str) -> str | None:
            raise VaultLockedError("vault locked")

    monkeypatch.setattr(app_settings_module, "_get_secretkeeper_client", lambda: _LockedClient())

    assert app_settings_module._read_secretkeeper_secret("AI_OPENAI_API_KEY") is None


def test_read_secretkeeper_secret_raises_unexpected_runtime_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BrokenClient:
        def get_or_none(self, _key: str) -> str | None:
            raise RuntimeError("boom")

    monkeypatch.setattr(app_settings_module, "_get_secretkeeper_client", lambda: _BrokenClient())

    with pytest.raises(RuntimeError, match="boom"):
        app_settings_module._read_secretkeeper_secret("AI_OPENAI_API_KEY")
