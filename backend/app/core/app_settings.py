"""
Application settings – single entry point for all backend configuration.

``AppSettings`` is assembled from domain-specific mixins (see
``app/core/settings/``).  Each mixin owns a coherent group of fields.
Consumers should call ``get_app_settings()`` and access fields directly.

Backward-compatible helper functions are provided at the bottom of this
module so that existing callers do not need to change immediately.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

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


@lru_cache
def get_app_settings() -> AppSettings:
    """Return the cached application settings instance."""
    return AppSettings()


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
        self.api_key: str = s.ai_openai_api_key or s.openai_api_key or ""
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
]

