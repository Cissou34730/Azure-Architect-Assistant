"""Typed configuration settings for ingestion."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables once at module import
load_dotenv()


class OpenAISettings(BaseModel):
    """OpenAI configuration loaded from environment variables."""
    
    api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    embedding_model: str = Field(default_factory=lambda: os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))


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
    embedder_type: str = Field(description="Type of embedder (openai, azure, etc.)")
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


# Global settings instances
_settings: Optional[IngestionSettings] = None
_kb_defaults: Optional[KBDefaults] = None
_openai_settings: Optional[OpenAISettings] = None


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


def get_openai_settings() -> OpenAISettings:
    """Get OpenAI settings instance (lazy-loaded from environment)."""
    global _openai_settings
    if _openai_settings is None:
        _openai_settings = OpenAISettings()
    return _openai_settings


def set_settings(settings: IngestionSettings) -> None:
    """Override global settings (useful for testing)."""
    global _settings
    _settings = settings
