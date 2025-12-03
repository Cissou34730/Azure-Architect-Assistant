"""Typed configuration settings for ingestion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class IngestionSettings(BaseModel):
    """Configuration for ingestion system - auto-loaded from JSON."""
    
    # Queue configuration
    batch_size: int = Field(description="Number of items to dequeue per batch")
    dequeue_timeout: float = Field(description="Seconds to wait when queue empty")
    consumer_poll_interval: float = Field(description="Seconds between dequeue attempts")
    
    # Thread lifecycle
    thread_join_timeout: float = Field(description="Seconds to wait for thread exit")

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_json(cls, config_path: Optional[Path] = None) -> "IngestionSettings":
        """Load settings from JSON configuration file."""
        if config_path is None:
            config_path = Path(__file__).parent / "ingestion.config.json"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Pydantic does all the parsing, validation, and type conversion
        return cls.parse_file(config_path)


class KBDefaults(BaseModel):
    """Default configuration for knowledge bases."""
    
    chunk_size: int = Field(description="Target size for text chunks")
    chunk_overlap: int = Field(description="Overlap between consecutive chunks")
    chunking_strategy: str = Field(description="Strategy for chunking (semantic, fixed, etc.)")
    embedding_model: str = Field(description="Model name for embeddings")
    embedder_type: str = Field(description="Type of embedder (openai, azure, etc.)")
    generation_model: str = Field(description="Model name for text generation")
    index_type: str = Field(description="Type of index (vector, summary, etc.)")

    @classmethod
    def from_json(cls, config_path: Optional[Path] = None) -> "KBDefaults":
        """Load KB defaults from JSON configuration file."""
        if config_path is None:
            config_path = Path(__file__).parent / "kb_defaults.json"
        
        if not config_path.exists():
            raise FileNotFoundError(f"KB defaults file not found: {config_path}")
        
        return cls.parse_file(config_path)
    
    def merge_with_kb_config(self, kb_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge defaults with KB-specific config (KB config takes precedence)."""
        defaults = self.dict()
        return {**defaults, **kb_config}


# Global settings instance
_settings: Optional[IngestionSettings] = None
_kb_defaults: Optional[KBDefaults] = None


def get_settings() -> IngestionSettings:
    """Get global settings instance (lazy-loaded from JSON config)."""
    global _settings
    if _settings is None:
        _settings = IngestionSettings.from_json()
    return _settings


def get_kb_defaults() -> KBDefaults:
    """Get KB defaults instance (lazy-loaded from JSON config)."""
    global _kb_defaults
    if _kb_defaults is None:
        _kb_defaults = KBDefaults.from_json()
    return _kb_defaults


def set_settings(settings: IngestionSettings) -> None:
    """Override global settings (useful for testing)."""
    global _settings
    _settings = settings
