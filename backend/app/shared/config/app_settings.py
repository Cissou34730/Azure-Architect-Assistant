"""Shared application settings entry point."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from typing import Protocol

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.shared.config.settings import (
    AgentsSettingsMixin,
    AISettingsMixin,
    AsyncTimingsMixin,
    DiagramSettingsMixin,
    IngestionQueueDefaults,
    IngestionSettingsMixin,
    KBDefaultsSettings,
    LLMTuningSettingsMixin,
    SearchSettingsMixin,
    ServerSettingsMixin,
    StorageSettingsMixin,
    WafSettingsMixin,
    get_default_env_path,
)
from app.shared.runtime.runtime_ai_selection import (
    RuntimeAISelection,
    load_runtime_ai_selection,
)

logger = logging.getLogger(__name__)


class _SecretKeeperClient(Protocol):
    def get_or_none(self, key: str) -> object: ...


def _is_expected_secretkeeper_error(exc: Exception) -> bool:
    return exc.__class__.__name__ in {
        "VaultLockedError",
        "VaultNotInitializedError",
        "KeyNotFoundError",
    }


@lru_cache
def _get_secretkeeper_client() -> _SecretKeeperClient | None:
    try:
        secretkeeper_module = import_module("secretkeeper")
    except ImportError:
        logger.debug("SecretKeeper SDK not installed; falling back to env settings")
        return None

    try:
        return secretkeeper_module.SecretKeeper()
    except Exception as exc:
        if _is_expected_secretkeeper_error(exc):
            logger.info("SecretKeeper unavailable during startup; using env fallback")
            return None
        raise


def _read_secretkeeper_secret(key: str) -> str | None:
    client = _get_secretkeeper_client()
    if client is None:
        return None

    try:
        value = client.get_or_none(key)
    except Exception as exc:
        if _is_expected_secretkeeper_error(exc):
            logger.info("SecretKeeper secret lookup unavailable for %s; using env fallback", key)
            return None
        raise

    return value if isinstance(value, str) and value else None


class AppSettings(
    ServerSettingsMixin,
    StorageSettingsMixin,
    AgentsSettingsMixin,
    AISettingsMixin,
    LLMTuningSettingsMixin,
    IngestionSettingsMixin,
    SearchSettingsMixin,
    WafSettingsMixin,
    AsyncTimingsMixin,
    DiagramSettingsMixin,
    BaseSettings,
):
    """Top-level application settings assembled from domain mixins."""

    model_config = SettingsConfigDict(
        env_file=str(get_default_env_path()),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def effective_openai_api_key(self) -> str:
        return (
            _read_secretkeeper_secret("AI_OPENAI_API_KEY")
            or self.ai_openai_api_key
            or self.openai_api_key
            or ""
        )

    @property
    def effective_azure_openai_endpoint(self) -> str:
        return _read_secretkeeper_secret("AI_AZURE_OPENAI_ENDPOINT") or self.ai_azure_openai_endpoint or ""

    @property
    def effective_azure_openai_api_key(self) -> str:
        return _read_secretkeeper_secret("AI_AZURE_OPENAI_API_KEY") or self.ai_azure_openai_api_key or ""

    @property
    def runtime_ai_selection(self) -> RuntimeAISelection | None:
        return load_runtime_ai_selection(self.runtime_ai_selection_path)

    @property
    def effective_ai_llm_provider(self) -> str:
        selection = self.runtime_ai_selection
        return selection.llm_provider if selection is not None else self.ai_llm_provider

    @property
    def effective_openai_llm_model(self) -> str:
        selection = self.runtime_ai_selection
        if selection is not None and selection.llm_provider == "openai":
            return selection.model_id
        return self.openai_model or self.ai_openai_llm_model

    def _configured_azure_llm_deployment_ids(self) -> set[str]:
        configured: set[str] = set()
        primary = _read_secretkeeper_secret("AI_AZURE_LLM_DEPLOYMENT") or self.ai_azure_llm_deployment
        if primary:
            configured.add(primary)

        additional = _read_secretkeeper_secret("AI_AZURE_LLM_DEPLOYMENTS") or self.ai_azure_llm_deployments
        if additional:
            configured.update(
                item.strip()
                for item in additional.split(",")
                if item.strip()
            )
        return configured

    @property
    def effective_azure_llm_deployment(self) -> str:
        primary = _read_secretkeeper_secret("AI_AZURE_LLM_DEPLOYMENT") or self.ai_azure_llm_deployment
        selection = self.runtime_ai_selection
        if selection is not None and selection.llm_provider == "azure":
            configured = self._configured_azure_llm_deployment_ids()
            if not configured or selection.model_id in configured:
                return selection.model_id
            logger.warning(
                "Ignoring runtime Azure deployment selection '%s' because it is not one of the configured deployment ids.",
                selection.model_id,
            )
        return primary

    @property
    def effective_azure_llm_deployments(self) -> str:
        return _read_secretkeeper_secret("AI_AZURE_LLM_DEPLOYMENTS") or self.ai_azure_llm_deployments or ""

    @property
    def effective_azure_embedding_deployment(self) -> str:
        return _read_secretkeeper_secret("AI_AZURE_EMBEDDING_DEPLOYMENT") or self.ai_azure_embedding_deployment or ""

    @property
    def effective_copilot_default_model(self) -> str:
        selection = self.runtime_ai_selection
        if selection is not None and selection.llm_provider == "copilot":
            return selection.model_id.lstrip("/")
        return self.ai_copilot_default_model.lstrip("/")

    @property
    def effective_copilot_token(self) -> str:
        return (
            _read_secretkeeper_secret("AI_COPILOT_TOKEN")
            or self.ai_copilot_token
            or os.environ.get("GITHUB_TOKEN", "")
        )


@lru_cache
def get_app_settings() -> AppSettings:
    return AppSettings()


def get_settings() -> AppSettings:
    return get_app_settings()


def get_backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_ingestion_settings() -> IngestionQueueDefaults:
    return get_app_settings().ingestion_queue


def get_kb_defaults() -> KBDefaultsSettings:
    return get_app_settings().kb_defaults


def get_kb_storage_root(raw: bool = False) -> Path:
    return get_app_settings().knowledge_bases_root


class _OpenAISettingsCompat:
    def __init__(self, settings: AppSettings) -> None:
        self.api_key: str = settings.effective_openai_api_key
        self.model: str = settings.effective_openai_llm_model
        self.embedding_model: str = settings.openai_embedding_model or settings.ai_openai_embedding_model


def get_openai_settings() -> _OpenAISettingsCompat:
    return _OpenAISettingsCompat(get_app_settings())


IngestionSettings = IngestionQueueDefaults
KBDefaults = KBDefaultsSettings

__all__ = [
    "AppSettings",
    "IngestionQueueDefaults",
    "IngestionSettings",
    "KBDefaults",
    "KBDefaultsSettings",
    "_get_secretkeeper_client",
    "_read_secretkeeper_secret",
    "get_app_settings",
    "get_backend_root",
    "get_ingestion_settings",
    "get_kb_defaults",
    "get_kb_storage_root",
    "get_openai_settings",
    "get_settings",
    "load_runtime_ai_selection",
]

