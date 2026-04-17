"""Tests for AI Foundry configuration resolution through SecretKeeper."""

from __future__ import annotations

from unittest.mock import patch

from app.shared.ai.config import AIConfig
from app.shared.config.app_settings import (
    AppSettings,
    _get_secretkeeper_client,
    get_app_settings,
)
from app.shared.runtime.runtime_ai_selection import (
    RuntimeAISelection,
    load_runtime_ai_selection,
)


def _make_settings(**overrides: object) -> AppSettings:
    """Build an AppSettings instance with .env reading disabled."""
    defaults: dict[str, object] = {
        "ai_foundry_endpoint": "",
        "ai_foundry_api_key": "",
        "ai_foundry_resource_id": "",
    }
    defaults.update(overrides)
    return AppSettings(**defaults)


def _clear_caches() -> None:
    """Clear LRU caches so SecretKeeper mocks take effect."""
    _get_secretkeeper_client.cache_clear()
    get_app_settings.cache_clear()


class TestEffectiveFoundryEndpoint:
    def setup_method(self) -> None:
        _clear_caches()

    def teardown_method(self) -> None:
        _clear_caches()

    def test_returns_secretkeeper_value_when_available(self) -> None:
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            side_effect={"AI_FOUNDRY_ENDPOINT": "https://vault-foundry.cognitiveservices.azure.com/"}.get,
        ):
            settings = _make_settings()
            assert settings.effective_foundry_endpoint == "https://vault-foundry.cognitiveservices.azure.com/"

    def test_falls_back_to_env_var_when_secretkeeper_empty(self) -> None:
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            return_value=None,
        ):
            settings = _make_settings(ai_foundry_endpoint="https://env-foundry.cognitiveservices.azure.com/")
            assert settings.effective_foundry_endpoint == "https://env-foundry.cognitiveservices.azure.com/"

    def test_returns_empty_when_neither_set(self) -> None:
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            return_value=None,
        ):
            settings = _make_settings()
            assert settings.effective_foundry_endpoint == ""


class TestEffectiveFoundryApiKey:
    def setup_method(self) -> None:
        _clear_caches()

    def teardown_method(self) -> None:
        _clear_caches()

    def test_returns_secretkeeper_value_when_available(self) -> None:
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            side_effect={"AI_FOUNDRY_API_KEY": "vault-key"}.get,
        ):
            settings = _make_settings()
            assert settings.effective_foundry_api_key == "vault-key"

    def test_falls_back_to_env_var_when_secretkeeper_empty(self) -> None:
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            return_value=None,
        ):
            settings = _make_settings(ai_foundry_api_key="env-key")
            assert settings.effective_foundry_api_key == "env-key"


class TestEffectiveFoundryResourceId:
    def setup_method(self) -> None:
        _clear_caches()

    def teardown_method(self) -> None:
        _clear_caches()

    def test_returns_secretkeeper_value_when_available(self) -> None:
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            side_effect={"AI_FOUNDRY_RESOURCE_ID": "/subscriptions/test/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/foundry"}.get,
        ):
            settings = _make_settings()
            assert settings.effective_foundry_resource_id == "/subscriptions/test/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/foundry"

    def test_falls_back_to_env_var_when_secretkeeper_empty(self) -> None:
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            return_value=None,
        ):
            settings = _make_settings(
                ai_foundry_resource_id="/subscriptions/env/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/foundry",
            )
            assert settings.effective_foundry_resource_id == "/subscriptions/env/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/foundry"


class TestAIConfigUsesEffectiveFoundryProperties:
    def setup_method(self) -> None:
        _clear_caches()

    def teardown_method(self) -> None:
        _clear_caches()

    def test_foundry_config_comes_from_effective_properties_and_runtime_selection(self) -> None:
        runtime_selection = RuntimeAISelection(
            llm_provider="foundry",
            model_id="gpt-5.3-chat",
        )

        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            side_effect={
                "AI_FOUNDRY_ENDPOINT": "https://sk-foundry.cognitiveservices.azure.com/",
                "AI_FOUNDRY_API_KEY": "sk-foundry-key",
                "AI_FOUNDRY_RESOURCE_ID": "/subscriptions/sk/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/foundry",
            }.get,
        ), patch(
            "app.shared.config.app_settings.load_runtime_ai_selection",
            return_value=runtime_selection,
        ):
            settings = _make_settings(
                ai_llm_provider="foundry",
                ai_embedding_provider="foundry",
            )
            config = AIConfig.from_settings(settings)
            assert config.foundry_endpoint == "https://sk-foundry.cognitiveservices.azure.com/"
            assert config.foundry_api_key == "sk-foundry-key"
            assert config.foundry_resource_id == "/subscriptions/sk/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/foundry"
            assert config.llm_provider == "foundry"
            assert config.embedding_provider == "foundry"
            assert config.foundry_model == "gpt-5.3-chat"
            assert config.active_llm_model == "gpt-5.3-chat"


def test_load_runtime_ai_selection_rejects_legacy_azure_provider(tmp_path) -> None:
    runtime_selection_path = tmp_path / "runtime_ai_selection.json"
    runtime_selection_path.write_text(
        '{"llm_provider": "azure", "model_id": "legacy-deployment"}',
        encoding="utf-8",
    )

    assert load_runtime_ai_selection(runtime_selection_path) is None

