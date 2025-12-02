"""Configuration module for ingestion."""

from .settings import (
    IngestionSettings,
    get_settings,
    set_settings,
)

__all__ = [
    "IngestionSettings",
    "get_settings",
    "set_settings",
]
