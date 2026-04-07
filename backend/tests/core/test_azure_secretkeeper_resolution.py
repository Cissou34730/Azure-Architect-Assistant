"""Tests for Azure OpenAI configuration resolution through SecretKeeper.

Verifies that AppSettings resolves Azure endpoint, deployment, and other
Azure config values via SecretKeeper before falling back to env vars.
"""

from __future__ import annotations

from unittest.mock import patch

from app.shared.ai.config import AIConfig
from app.shared.config.app_settings import (
    AppSettings,
    _get_secretkeeper_client,
    get_app_settings,
)
from app.shared.runtime.runtime_ai_selection import RuntimeAISelection

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(**overrides):
    """Build an AppSettings instance with .env reading disabled."""
    defaults = {
        "ai_azure_openai_endpoint": "",
        "ai_azure_openai_api_key": "",
        "ai_azure_llm_deployment": "",
        "ai_azure_llm_deployments": "",
        "ai_azure_embedding_deployment": "",
    }
    defaults.update(overrides)
    return AppSettings(**defaults)


def _clear_caches():
    """Clear LRU caches so SecretKeeper mock takes effect."""
    _get_secretkeeper_client.cache_clear()
    get_app_settings.cache_clear()


# ---------------------------------------------------------------------------
# effective_azure_openai_endpoint
# ---------------------------------------------------------------------------

class TestEffectiveAzureOpenaiEndpoint:
    """AppSettings.effective_azure_openai_endpoint resolves via SecretKeeper."""

    def setup_method(self):
        _clear_caches()

    def teardown_method(self):
        _clear_caches()

    def test_returns_secretkeeper_value_when_available(self):
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            side_effect={"AI_AZURE_OPENAI_ENDPOINT": "https://vault-endpoint.openai.azure.com/"}.get,
        ):
            settings = _make_settings()
            assert settings.effective_azure_openai_endpoint == "https://vault-endpoint.openai.azure.com/"

    def test_falls_back_to_env_var_when_secretkeeper_empty(self):
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            return_value=None,
        ):
            settings = _make_settings(ai_azure_openai_endpoint="https://env-endpoint.openai.azure.com/")
            assert settings.effective_azure_openai_endpoint == "https://env-endpoint.openai.azure.com/"

    def test_returns_empty_when_neither_set(self):
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            return_value=None,
        ):
            settings = _make_settings()
            assert settings.effective_azure_openai_endpoint == ""


# ---------------------------------------------------------------------------
# effective_azure_llm_deployment — SecretKeeper fallback
# ---------------------------------------------------------------------------

class TestEffectiveAzureLlmDeploymentSecretKeeper:
    """effective_azure_llm_deployment should check SecretKeeper when no runtime override."""

    def setup_method(self):
        _clear_caches()

    def teardown_method(self):
        _clear_caches()

    def test_returns_secretkeeper_value_when_no_runtime_override(self):
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            side_effect={"AI_AZURE_LLM_DEPLOYMENT": "vault-deployment"}.get,
        ), patch(
            "app.shared.config.app_settings.load_runtime_ai_selection",
            return_value=None,
        ):
            settings = _make_settings()
            assert settings.effective_azure_llm_deployment == "vault-deployment"

    def test_runtime_override_takes_precedence_over_secretkeeper(self):
        mock_selection = RuntimeAISelection(llm_provider="azure", model_id="runtime-deploy")

        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            side_effect={
                "AI_AZURE_LLM_DEPLOYMENT": "vault-deployment",
                "AI_AZURE_LLM_DEPLOYMENTS": "vault-deployment,runtime-deploy",
            }.get,
        ), patch(
            "app.shared.config.app_settings.load_runtime_ai_selection",
            return_value=mock_selection,
        ):
            settings = _make_settings()
            assert settings.effective_azure_llm_deployment == "runtime-deploy"

    def test_invalid_runtime_override_falls_back_to_configured_deployment(self):
        mock_selection = RuntimeAISelection(llm_provider="azure", model_id="gpt-4o")

        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            side_effect={
                "AI_AZURE_LLM_DEPLOYMENT": "vault-deployment",
                "AI_AZURE_LLM_DEPLOYMENTS": "vault-deployment,backup-deployment",
            }.get,
        ), patch(
            "app.shared.config.app_settings.load_runtime_ai_selection",
            return_value=mock_selection,
        ):
            settings = _make_settings()
            assert settings.effective_azure_llm_deployment == "vault-deployment"


# ---------------------------------------------------------------------------
# effective_azure_llm_deployments
# ---------------------------------------------------------------------------

class TestEffectiveAzureLlmDeployments:
    """AppSettings.effective_azure_llm_deployments resolves via SecretKeeper."""

    def setup_method(self):
        _clear_caches()

    def teardown_method(self):
        _clear_caches()

    def test_returns_secretkeeper_value_when_available(self):
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            side_effect={"AI_AZURE_LLM_DEPLOYMENTS": "deploy-a,deploy-b"}.get,
        ):
            settings = _make_settings()
            assert settings.effective_azure_llm_deployments == "deploy-a,deploy-b"

    def test_falls_back_to_env_var(self):
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            return_value=None,
        ):
            settings = _make_settings(ai_azure_llm_deployments="env-deploy")
            assert settings.effective_azure_llm_deployments == "env-deploy"


# ---------------------------------------------------------------------------
# effective_azure_embedding_deployment
# ---------------------------------------------------------------------------

class TestEffectiveAzureEmbeddingDeployment:
    """AppSettings.effective_azure_embedding_deployment resolves via SecretKeeper."""

    def setup_method(self):
        _clear_caches()

    def teardown_method(self):
        _clear_caches()

    def test_returns_secretkeeper_value_when_available(self):
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            side_effect={"AI_AZURE_EMBEDDING_DEPLOYMENT": "vault-embedding"}.get,
        ):
            settings = _make_settings()
            assert settings.effective_azure_embedding_deployment == "vault-embedding"

    def test_falls_back_to_env_var(self):
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            return_value=None,
        ):
            settings = _make_settings(ai_azure_embedding_deployment="env-embedding")
            assert settings.effective_azure_embedding_deployment == "env-embedding"


# ---------------------------------------------------------------------------
# AIConfig.from_settings uses effective properties
# ---------------------------------------------------------------------------

class TestAIConfigUsesEffectiveAzureProperties:
    """AIConfig.from_settings() should route through effective_ properties."""

    def setup_method(self):
        _clear_caches()

    def teardown_method(self):
        _clear_caches()

    def test_azure_endpoint_comes_from_effective_property(self):
        with patch(
            "app.shared.config.app_settings._read_secretkeeper_secret",
            side_effect={
                "AI_AZURE_OPENAI_ENDPOINT": "https://sk-endpoint.openai.azure.com/",
                "AI_AZURE_OPENAI_API_KEY": "sk-key",
                "AI_AZURE_LLM_DEPLOYMENT": "sk-deploy",
                "AI_AZURE_LLM_DEPLOYMENTS": "sk-deploy",
                "AI_AZURE_EMBEDDING_DEPLOYMENT": "sk-embed",
            }.get,
        ), patch(
            "app.shared.config.app_settings.load_runtime_ai_selection",
            return_value=None,
        ):
            settings = _make_settings()
            config = AIConfig.from_settings(settings)
            assert config.azure_openai_endpoint == "https://sk-endpoint.openai.azure.com/"
            assert config.azure_openai_api_key == "sk-key"
            assert config.azure_llm_deployment == "sk-deploy"
            assert config.azure_llm_deployments == "sk-deploy"
            assert config.azure_embedding_deployment == "sk-embed"

