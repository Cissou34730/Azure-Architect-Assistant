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
        
        # Create instance with defaults, then override from config
        instance = cls()
        if "data_root" in config:
            instance.data_root = Path(config["data_root"])
        if "batch_size" in config:
            instance.batch_size = int(config["batch_size"])
        if "dequeue_timeout" in config:
            instance.dequeue_timeout = float(config["dequeue_timeout"])
        if "consumer_poll_interval" in config:
            instance.consumer_poll_interval = float(config["consumer_poll_interval"])
        if "thread_join_timeout" in config:
            instance.thread_join_timeout = float(config["thread_join_timeout"])
        if "shutdown_grace_period" in config:
            instance.shutdown_grace_period = float(config["shutdown_grace_period"])
        if "max_retries" in config:
            instance.max_retries = int(config["max_retries"])
        if "retry_delay" in config:
            instance.retry_delay = float(config["retry_delay"])
        if "persistence_backend" in config:
            instance.persistence_backend = config["persistence_backend"]
        if "state_file_name" in config:
            instance.state_file_name = config["state_file_name"]
        if "log_level" in config:
            instance.log_level = config["log_level"]
        if "enable_correlation_ids" in config:
            instance.enable_correlation_ids = config["enable_correlation_ids"]
        if "enable_metrics" in config:
            instance.enable_metrics = config["enable_metrics"]
        if "metrics_backend" in config:
            instance.metrics_backend = config["metrics_backend"]
        if "metrics_port" in config:
            instance.metrics_port = int(config["metrics_port"])
        
        return instance


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
