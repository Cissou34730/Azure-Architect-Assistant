import pytest
from unittest.mock import patch

import app.shared.config.app_settings as app_settings_module
from app.shared.ai.ai_service import AIService, AIServiceManager
from app.shared.ai.config import AIConfig
from app.shared.ai.providers import FoundryEmbeddingProvider, FoundryLLMProvider
from app.shared.config.app_settings import AppSettings


def _base_openai_config() -> dict:
    return {
        "openai_api_key": "test-openai-key",
        "openai_llm_model": "gpt-4o-mini",
        "openai_embedding_model": "text-embedding-3-small",
    }


def _foundry_fields() -> dict:
    return {
        "foundry_endpoint": "https://example.services.ai.azure.com",
        "foundry_api_key": "test-foundry-key",
        "foundry_resource_id": "/subscriptions/test/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/foundry",
        "foundry_model": "gpt-5.3-chat",
        "foundry_embedding_model": "text-embedding-3-small",
    }


def test_validate_requires_foundry_fields_when_foundry_is_selected() -> None:
    config = AIConfig(
        llm_provider="foundry",
        embedding_provider="foundry",
    )

    with pytest.raises(ValueError, match="Foundry endpoint, API key"):
        config.validate_provider_config()


def test_validate_foundry_embeddings_do_not_require_explicit_embedding_model() -> None:
    config = AIConfig(
        llm_provider="foundry",
        embedding_provider="foundry",
        foundry_endpoint="https://example.services.ai.azure.com",
        foundry_api_key="test-foundry-key",
        foundry_resource_id="/subscriptions/test/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/foundry",
        foundry_model="gpt-5.3-chat",
    )

    config.validate_provider_config()


def test_validate_requires_openai_key_when_openai_is_selected() -> None:
    config = AIConfig(
        **_foundry_fields(),
        llm_provider="foundry",
        embedding_provider="openai",
    )

    with pytest.raises(ValueError, match="OpenAI API key"):
        config.validate_provider_config()


def test_ai_service_builds_foundry_providers() -> None:
    config = AIConfig(
        **_foundry_fields(),
        llm_provider="foundry",
        embedding_provider="foundry",
    )

    service = AIService(config)

    assert isinstance(service._llm_provider, FoundryLLMProvider)
    assert isinstance(service._embedding_provider, FoundryEmbeddingProvider)


def test_create_chat_llm_uses_foundry_azure_chat_openai() -> None:
    config = AIConfig(
        **_foundry_fields(),
        llm_provider="foundry",
        embedding_provider="foundry",
        default_temperature=0.3,
    )
    service = AIService(config)

    with patch("langchain_openai.AzureChatOpenAI") as mock_chat_model:
        service.create_chat_llm()

    mock_chat_model.assert_called_once_with(
        azure_deployment="gpt-5.3-chat",
        api_version=config.foundry_api_version,
        azure_endpoint=config.foundry_endpoint,
        api_key=config.foundry_api_key,
        temperature=0.3,
    )


def test_build_config_for_selection_uses_foundry_runtime_model() -> None:
    base_config = AIConfig(
        **_foundry_fields(),
        llm_provider="openai",
        embedding_provider="foundry",
        **_base_openai_config(),
    )

    updated = AIServiceManager._build_config_for_selection(
        "foundry",
        "Phi-4",
        base_config=base_config,
    )

    assert updated.llm_provider == "foundry"
    assert updated.foundry_model == "Phi-4"


def test_build_config_for_selection_rejects_legacy_azure_provider() -> None:
    base_config = AIConfig(
        **_foundry_fields(),
        llm_provider="openai",
        embedding_provider="foundry",
        **_base_openai_config(),
    )

    with pytest.raises(ValueError, match="Provider 'azure' is no longer supported. Use 'foundry'."):
        AIServiceManager._build_config_for_selection(
            "azure",
            "legacy-deployment",
            base_config=base_config,
        )


def test_app_settings_effective_keys_prefer_secretkeeper(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "AI_OPENAI_API_KEY": "sk-openai-key",
        "AI_FOUNDRY_API_KEY": "sk-foundry-key",
    }
    monkeypatch.setattr("app.shared.config.app_settings._read_secretkeeper_secret", lambda key: values.get(key))

    settings = AppSettings(
        ai_openai_api_key="env-openai-key",
        ai_foundry_api_key="env-foundry-key",
        openai_api_key="legacy-openai-key",
    )

    assert settings.effective_openai_api_key == "sk-openai-key"
    assert settings.effective_foundry_api_key == "sk-foundry-key"


def test_app_settings_effective_keys_fall_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.shared.config.app_settings._read_secretkeeper_secret", lambda _key: None)

    settings = AppSettings(
        ai_openai_api_key="",
        ai_foundry_api_key="env-foundry-key",
        openai_api_key="legacy-openai-key",
    )

    assert settings.effective_openai_api_key == "legacy-openai-key"
    assert settings.effective_foundry_api_key == "env-foundry-key"


def test_app_settings_effective_openai_key_empty_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.shared.config.app_settings._read_secretkeeper_secret", lambda _key: None)

    settings = AppSettings(ai_openai_api_key="", openai_api_key=None)

    assert settings.effective_openai_api_key == ""


def test_app_settings_effective_llm_selection_uses_runtime_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr("app.shared.config.app_settings._read_secretkeeper_secret", lambda _key: None)
    runtime_selection_path = tmp_path / "runtime_ai_selection.json"
    runtime_selection_path.write_text(
        '{"llm_provider": "copilot", "model_id": "gpt-4o"}',
        encoding="utf-8",
    )

    settings = AppSettings(
        data_root=tmp_path,
        projects_database=tmp_path / "projects.db",
        ingestion_database=tmp_path / "ingestion.db",
        diagrams_database=tmp_path / "diagrams.db",
        models_cache_path=tmp_path / "models_cache.json",
        knowledge_bases_root=tmp_path / "knowledge_bases",
        project_documents_root=tmp_path / "project_documents",
        waf_template_cache_dir=tmp_path / "waf_template_cache",
        ai_llm_provider="openai",
        ai_openai_llm_model="gpt-4o-mini",
        ai_copilot_default_model="gpt-5.2",
        openai_api_key="legacy-openai-key",
    )

    config = AIConfig.from_settings(settings)

    assert settings.effective_ai_llm_provider == "copilot"
    assert config.llm_provider == "copilot"
    assert config.copilot_default_model == "gpt-4o"


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

