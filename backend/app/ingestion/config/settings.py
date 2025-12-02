"""Typed configuration settings for ingestion."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class IngestionSettings:
    """Configuration for ingestion system."""

    # Paths
    data_root: Path = field(default_factory=lambda: Path("data/knowledge_bases"))
    
    # Queue configuration
    batch_size: int = 50
    dequeue_timeout: float = 0.1  # seconds to wait when queue empty
    consumer_poll_interval: float = 0.1  # seconds between dequeue attempts
    
    # Thread lifecycle
    thread_join_timeout: float = 5.0  # seconds to wait for thread exit
    shutdown_grace_period: float = 30.0  # max seconds for graceful shutdown
    
    # Retry policy
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds between retries
    
    # Persistence
    persistence_backend: str = "local_disk"  # local_disk | azure_files | azure_blob
    state_file_name: str = "state.json"
    
    # Logging
    log_level: str = "INFO"
    enable_correlation_ids: bool = True
    
    # Metrics
    enable_metrics: bool = True
    metrics_backend: str = "prometheus"  # prometheus | otlp | none
    metrics_port: int = 9090

    @classmethod
    def from_json(cls, config_path: Optional[Path] = None) -> "IngestionSettings":
        """Load settings from JSON configuration file."""
        if config_path is None:
            # Default to config file in same directory
            config_path = Path(__file__).parent / "ingestion.config.json"
        
        if not config_path.exists():
            # Return defaults if config file doesn't exist
            return cls()
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return cls(
            data_root=Path(config.get("data_root", "data/knowledge_bases")),
            batch_size=int(config.get("batch_size", 50)),
            dequeue_timeout=float(config.get("dequeue_timeout", 0.1)),
            consumer_poll_interval=float(config.get("consumer_poll_interval", 0.1)),
            thread_join_timeout=float(config.get("thread_join_timeout", 5.0)),
            shutdown_grace_period=float(config.get("shutdown_grace_period", 30.0)),
            max_retries=int(config.get("max_retries", 3)),
            retry_delay=float(config.get("retry_delay", 1.0)),
            persistence_backend=config.get("persistence_backend", "local_disk"),
            state_file_name=config.get("state_file_name", "state.json"),
            log_level=config.get("log_level", "INFO"),
            enable_correlation_ids=config.get("enable_correlation_ids", True),
            enable_metrics=config.get("enable_metrics", True),
            metrics_backend=config.get("metrics_backend", "prometheus"),
            metrics_port=int(config.get("metrics_port", 9090)),
        )


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
