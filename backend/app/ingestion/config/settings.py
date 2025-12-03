"""Typed configuration settings for ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class IngestionSettings(BaseModel):
    """Configuration for ingestion system - auto-loaded from JSON."""
    
    # Queue configuration
    batch_size: int = Field(default=50, description="Number of items to dequeue per batch")
    dequeue_timeout: float = Field(default=0.1, description="Seconds to wait when queue empty")
    consumer_poll_interval: float = Field(default=0.1, description="Seconds between dequeue attempts")
    
    # Thread lifecycle
    thread_join_timeout: float = Field(default=5.0, description="Seconds to wait for thread exit")

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_json(cls, config_path: Optional[Path] = None) -> "IngestionSettings":
        """Load settings from JSON configuration file."""
        if config_path is None:
            config_path = Path(__file__).parent / "ingestion.config.json"
        
        if not config_path.exists():
            return cls()
        
        # Pydantic does all the parsing, validation, and type conversion
        return cls.parse_file(config_path)


# Global settings instance
_settings: Optional[IngestionSettings] = None


def get_settings() -> IngestionSettings:
    """Get global settings instance (lazy-loaded from JSON config)."""
    global _settings
    if _settings is None:
        _settings = IngestionSettings.from_json()
    return _settings


def set_settings(settings: IngestionSettings) -> None:
    """Override global settings (useful for testing)."""
    global _settings
    _settings = settings
