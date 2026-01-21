"""Typed configuration settings for ingestion."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables once at module import
load_dotenv()


class OpenAISettings(BaseModel):
    """OpenAI configuration loaded from environment variables."""

    api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    embedding_model: str = Field(
        default_factory=lambda: os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        )
    )


class IngestionSettings(BaseModel):
    """Configuration for ingestion system - auto-loaded from JSON."""

    # Queue configuration
    batch_size: int = Field(description="Number of items to dequeue per batch")
    dequeue_timeout: float = Field(description="Seconds to wait when queue empty")
    consumer_poll_interval: float = Field(
        description="Seconds between dequeue attempts"
    )

    # Thread lifecycle
    thread_join_timeout: float = Field(description="Seconds to wait for thread exit")

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_json(cls, config_path: Path | None = None) -> IngestionSettings:
        """Load settings from JSON configuration file."""
        if config_path is None:
            config_path = Path(__file__).parent / "ingestion.config.json"

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Pydantic v2: load JSON and validate explicitly
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)


class KBDefaults(BaseModel):
    """Default configuration for knowledge bases."""

    chunk_size: int = Field(description="Target size for text chunks")
    chunk_overlap: int = Field(description="Overlap between consecutive chunks")
    chunking_strategy: str = Field(
        description="Strategy for chunking (semantic, fixed, etc.)"
    )
    embedder_type: str = Field(description="Type of embedder (openai, azure, etc.)")
    index_type: str = Field(description="Type of index (vector, summary, etc.)")

    @classmethod
    def from_json(cls, config_path: Path | None = None) -> KBDefaults:
        """Load KB defaults from JSON configuration file."""
        if config_path is None:
            config_path = Path(__file__).parent / "kb_defaults.json"

        if not config_path.exists():
            raise FileNotFoundError(f"KB defaults file not found: {config_path}")

        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)

    def merge_with_kb_config(self, kb_config: dict[str, Any]) -> dict[str, Any]:
        """Merge defaults with KB-specific config and environment variables.
        Priority: kb_config > defaults > environment variables
        """
        # Start with JSON defaults
        merged = self.dict()

        # Add models from environment (will be overridden if in kb_config)
        openai_settings = get_openai_settings()
        merged["embedding_model"] = openai_settings.embedding_model
        merged["generation_model"] = openai_settings.model

        # KB-specific config takes precedence
        merged.update(kb_config)

        return merged


class SettingsContainer:
    """Container for global settings singletons."""
    settings: IngestionSettings | None = None
    kb_defaults: KBDefaults | None = None
    openai_settings: OpenAISettings | None = None
    kb_storage_root: Path | None = None
    kb_storage_root_raw: str | None = None


def get_settings() -> IngestionSettings:
    """Get global settings instance (lazy-loaded from JSON config)."""
    if SettingsContainer.settings is None:
        SettingsContainer.settings = IngestionSettings.from_json()
    return SettingsContainer.settings


def get_kb_defaults() -> KBDefaults:
    """Get KB defaults instance (lazy-loaded from JSON config)."""
    if SettingsContainer.kb_defaults is None:
        SettingsContainer.kb_defaults = KBDefaults.from_json()
    return SettingsContainer.kb_defaults


def get_openai_settings() -> OpenAISettings:
    """Get OpenAI settings instance (lazy-loaded from environment)."""
    if SettingsContainer.openai_settings is None:
        SettingsContainer.openai_settings = OpenAISettings()
    return SettingsContainer.openai_settings


def set_settings(settings: IngestionSettings) -> None:
    """Override global settings (useful for testing)."""
    SettingsContainer.settings = settings


def get_kb_storage_root(raw: bool = False) -> Path | str:
    """Get the configured knowledge base storage root.

    Args:
        raw: When True, return the raw environment value (may be relative).

    Returns:
        Absolute Path to the storage root by default, or the raw string value when requested.
    """
    if SettingsContainer.kb_storage_root is None or SettingsContainer.kb_storage_root_raw is None:
        backend_root = Path(__file__).resolve().parent.parent
        kb_root_env = os.getenv("KNOWLEDGE_BASES_ROOT", "data/knowledge_bases")
        kb_root_path = Path(kb_root_env)
        if not kb_root_path.is_absolute():
            kb_root_path = backend_root / kb_root_path

        SettingsContainer.kb_storage_root = kb_root_path
        SettingsContainer.kb_storage_root_raw = kb_root_env

    if raw:
        if SettingsContainer.kb_storage_root_raw is None:
             raise RuntimeError("KB Storage Root Raw not initialized")
        return SettingsContainer.kb_storage_root_raw

    if SettingsContainer.kb_storage_root is None:
        raise RuntimeError("KB Storage Root not initialized")
    return SettingsContainer.kb_storage_root

