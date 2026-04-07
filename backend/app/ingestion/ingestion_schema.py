"""Compatibility re-export — canonical module is at app.features.ingestion.infrastructure.ingestion_schema."""

from app.features.ingestion.infrastructure.ingestion_schema import (
    run_migrations,
)

__all__ = ["run_migrations"]
