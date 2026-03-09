"""
Application settings - single entry point for all backend configuration.

``AppSettings`` is assembled from domain-specific mixins (see
``app/core/settings/``).  Each mixin owns a coherent group of fields.
Consumers should call ``get_app_settings()`` and access fields directly.

Backward-compatible helper functions are provided at the bottom of this
module so that existing callers do not need to change immediately.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from typing import Protocol

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.settings import (
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

logger = logging.getLogger(__name__)


class _SecretKeeperClient(Protocol):
    def get_or_none(self, key: str) -> object: ...


def _is_expected_secretkeeper_error(exc: Exception) -> bool:
    """Return True for non-fatal SecretKeeper runtime states."""
    return exc.__class__.__name__ in {
        "VaultLockedError",
        "VaultNotInitializedError",
        "KeyNotFoundError",
    }


@lru_cache
def _get_secretkeeper_client() -> _SecretKeeperClient | None:
    """Create and cache SecretKeeper client when SDK and vault are available."""
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
    """Read secret by key; return None if unavailable/missing/invalid."""
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
        extra="ignore",  # env files may contain frontend-only keys; ignore safely
    )

    @property
    def effective_openai_api_key(self) -> str:
        """Resolve OpenAI key through SecretKeeper."""
        return (
            _read_secretkeeper_secret("AI_OPENAI_API_KEY")
            or self.ai_openai_api_key
            or self.openai_api_key
            or ""
        )

    @property
    def effective_azure_openai_api_key(self) -> str:
        """Resolve Azure OpenAI key through SecretKeeper."""
        return _read_secretkeeper_secret("AI_AZURE_OPENAI_API_KEY") or self.ai_azure_openai_api_key or ""


@lru_cache
def get_app_settings() -> AppSettings:
    """Return the cached application settings instance."""
    return AppSettings()


def get_settings() -> AppSettings:
    """Compat alias for legacy callers expecting get_settings()."""
    return get_app_settings()


def get_backend_root() -> Path:
    """Backend root directory path."""
    return Path(__file__).resolve().parents[2]


def get_ingestion_settings() -> IngestionQueueDefaults:
    """Compat: returns ingestion queue defaults (previously returned IngestionSettings)."""
    return get_app_settings().ingestion_queue


def get_kb_defaults() -> KBDefaultsSettings:
    """Compat: returns KB defaults sub-model."""
    return get_app_settings().kb_defaults


def get_kb_storage_root(raw: bool = False) -> Path:
    """Compat: returns absolute knowledge-base storage root.

    The ``raw`` parameter is ignored; AppSettings always stores an absolute path.
    """
    return get_app_settings().knowledge_bases_root  # type: ignore[return-value]


class _OpenAISettingsCompat:
    """Thin wrapper so legacy callers using ``get_openai_settings().model`` still work."""

    def __init__(self, s: AppSettings) -> None:
        self.api_key: str = s.effective_openai_api_key
        self.model: str = s.openai_model or s.ai_openai_llm_model
        self.embedding_model: str = s.openai_embedding_model or s.ai_openai_embedding_model


def get_openai_settings() -> _OpenAISettingsCompat:
    """Compat: returns object with .api_key, .model, .embedding_model."""
    return _OpenAISettingsCompat(get_app_settings())


# ── Type aliases kept for import compat ──────────────────────────────────────
IngestionSettings = IngestionQueueDefaults
KBDefaults = KBDefaultsSettings

__all__ = [
    "AppSettings",
    "IngestionQueueDefaults",
    "IngestionSettings",
    "KBDefaults",
    "KBDefaultsSettings",
    "get_app_settings",
    "get_backend_root",
    "get_ingestion_settings",
    "get_kb_defaults",
    "get_kb_storage_root",
    "get_openai_settings",
    "get_settings",
]

