import pytest

import app.shared.config.app_settings as app_settings_module
from app.shared.ai.ai_service import AIService
from app.shared.ai.config import AIConfig
from app.shared.ai.providers import AzureOpenAILLMProvider
from app.shared.config.app_settings import AppSettings


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


def test_validate_azure_llm_fallback_does_not_require_embedding_deployment() -> None:
    """Azure as LLM fallback should NOT require embedding deployment."""
    config = AIConfig(
        **_base_openai_config(),
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_api_key="test-azure-key",
        azure_llm_deployment="gpt-4o-mini-deployment",
        # No azure_embedding_deployment — intentionally omitted
        fallback_enabled=True,
        fallback_provider="azure",
        llm_provider="openai",
        embedding_provider="openai",
    )

    # Should NOT raise — embedding deployment is not needed for LLM-only fallback
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


def test_ai_service_builds_azure_llm_fallback_only() -> None:
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
    # Embedding fallback is always disabled (dimension mismatch risk)
    assert service._fallback_embedding_provider is None


def test_app_settings_effective_keys_prefer_secretkeeper(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "AI_OPENAI_API_KEY": "sk-openai-key",
        "AI_AZURE_OPENAI_API_KEY": "sk-azure-key",
    }
    monkeypatch.setattr("app.shared.config.app_settings._read_secretkeeper_secret", lambda key: values.get(key))

    settings = AppSettings(
        ai_openai_api_key="env-openai-key",
        ai_azure_openai_api_key="env-azure-key",
        openai_api_key="legacy-openai-key",
    )

    assert settings.effective_openai_api_key == "sk-openai-key"
    assert settings.effective_azure_openai_api_key == "sk-azure-key"


def test_app_settings_effective_keys_fall_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.shared.config.app_settings._read_secretkeeper_secret", lambda _key: None)

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

