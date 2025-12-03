"""Typed configuration settings for ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class IngestionSettings(BaseModel):
    """Configuration for ingestion system - auto-loaded from JSON."""

    # Paths
    data_root: Path = Field(default=Path("data/knowledge_bases"))
    
    # Queue configuration
    batch_size: int = Field(default=50)
    dequeue_timeout: float = Field(default=0.1, description="seconds to wait when queue empty")
    consumer_poll_interval: float = Field(default=0.1, description="seconds between dequeue attempts")
    
    # Thread lifecycle
    thread_join_timeout: float = Field(default=5.0, description="seconds to wait for thread exit")
    shutdown_grace_period: float = Field(default=30.0, description="max seconds for graceful shutdown")
    
    # Retry policy
    max_retries: int = Field(default=3)
    retry_delay: float = Field(default=1.0, description="seconds between retries")
    
    # Persistence
    persistence_backend: str = Field(default="local_disk", description="local_disk | azure_files | azure_blob")
    state_file_name: str = Field(default="state.json")
    
    # Logging
    log_level: str = Field(default="INFO")
    enable_correlation_ids: bool = Field(default=True)
    
    # Metrics
    enable_metrics: bool = Field(default=True)
    metrics_backend: str = Field(default="prometheus", description="prometheus | otlp | none")
    metrics_port: int = Field(default=9090)

    class Config:
        # Allow arbitrary types (like Path)
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
