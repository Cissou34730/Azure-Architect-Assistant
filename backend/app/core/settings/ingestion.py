"""Ingestion queue and knowledge-base defaults mixin.

The sub-models ``IngestionQueueDefaults`` and ``KBDefaultsSettings`` carry the
same runtime values that were previously loaded from
``backend/config/ingestion.config.json`` and ``backend/config/kb_defaults.json``.

Defaults in Python code mirror the JSON files; the JSON files are still
respected at runtime via the ``default_factory`` loaders below.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

# Anchors – this file lives at backend/app/core/settings/ingestion.py
_CONFIG_DIR: Path = Path(__file__).resolve().parents[3] / "config"


class IngestionQueueDefaults(BaseModel):
    """Queue / threading parameters for the ingestion pipeline."""

    batch_size: int = Field(50, description="Number of items to dequeue per batch")
    dequeue_timeout: float = Field(0.1, description="Seconds to wait when queue empty")
    consumer_poll_interval: float = Field(0.1, description="Seconds between dequeue attempts")
    thread_join_timeout: float = Field(5.0, description="Seconds to wait for thread exit")


class KBDefaultsSettings(BaseModel):
    """Default configuration applied when creating a new knowledge base."""

    chunk_size: int = Field(800, description="Target size for text chunks")
    chunk_overlap: int = Field(150, description="Overlap between consecutive chunks")
    chunking_strategy: str = Field("semantic", description="Chunking strategy")
    embedder_type: str = Field("openai", description="Embedder type")
    index_type: str = Field("vector", description="Index type")


def _load_ingestion_queue() -> IngestionQueueDefaults:
    """Load from ingestion.config.json if present, otherwise use code defaults."""
    json_path = _CONFIG_DIR / "ingestion.config.json"
    if json_path.exists():
        try:
            return IngestionQueueDefaults.model_validate(
                json.loads(json_path.read_text(encoding="utf-8"))
            )
        except Exception:  # noqa: BLE001
            pass
    return IngestionQueueDefaults()


def _load_kb_defaults() -> KBDefaultsSettings:
    """Load from kb_defaults.json if present, otherwise use code defaults."""
    json_path = _CONFIG_DIR / "kb_defaults.json"
    if json_path.exists():
        try:
            return KBDefaultsSettings.model_validate(
                json.loads(json_path.read_text(encoding="utf-8"))
            )
        except Exception:  # noqa: BLE001
            pass
    return KBDefaultsSettings()


class IngestionSettingsMixin(BaseModel):
    ingestion_queue: IngestionQueueDefaults = Field(
        default_factory=_load_ingestion_queue,
        description="Ingestion queue / threading parameters (loaded from ingestion.config.json)",
    )
    kb_defaults: KBDefaultsSettings = Field(
        default_factory=_load_kb_defaults,
        description="Default KB creation parameters (loaded from kb_defaults.json)",
    )
