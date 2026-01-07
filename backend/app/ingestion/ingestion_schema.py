"""Lightweight schema migration utilities for ingestion tables."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Table, Column, Integer, DateTime, MetaData, text
from sqlalchemy.engine import Engine

from app.ingestion.models import Base

SCHEMA_VERSION = 2  # Updated for ingestion_phase_status table


def _ensure_version_table(engine: Engine) -> MetaData:
    metadata = MetaData()
    Table(
        "ingestion_schema_version",
        metadata,
        Column("version", Integer, primary_key=True),
        Column("applied_at", DateTime, nullable=False),
    )
    metadata.create_all(engine)
    return metadata


def run_migrations(engine: Engine) -> None:
    """Apply pending migrations for the ingestion schema."""
    _ensure_version_table(engine)

    with engine.begin() as connection:
        result = connection.execute(
            text(
                "SELECT version FROM ingestion_schema_version ORDER BY version DESC LIMIT 1"
            )
        )
        current_version = result.scalar_one_or_none()

        if current_version is None:
            connection.execute(
                text(
                    "INSERT INTO ingestion_schema_version (version, applied_at) VALUES (:version, :applied_at)"
                ),
                {"version": SCHEMA_VERSION, "applied_at": datetime.now(timezone.utc)},
            )
        elif current_version > SCHEMA_VERSION:
            raise RuntimeError(
                "Database schema version is newer than supported ingestion migrations."
            )
        elif current_version < SCHEMA_VERSION:
            # Placeholder for future incremental migrations.
            connection.execute(
                text(
                    "UPDATE ingestion_schema_version SET version = :version, applied_at = :applied_at"
                ),
                {"version": SCHEMA_VERSION, "applied_at": datetime.now(timezone.utc)},
            )

        Base.metadata.create_all(bind=connection)
