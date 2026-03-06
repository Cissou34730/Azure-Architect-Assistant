"""Schema migration utilities for ingestion tables."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_CFG_PATH = _BACKEND_ROOT / 'alembic_ingestion.ini'
_LEGACY_BASE_REVISION = 'a1b2c3d4e5f6'


def _make_alembic_config(engine: Engine) -> Config:
    cfg = Config(str(_ALEMBIC_CFG_PATH))
    cfg.set_main_option('sqlalchemy.url', str(engine.url))
    cfg.attributes['skip_file_config'] = True
    return cfg


def run_migrations(engine: Engine) -> None:
    """Apply Alembic migrations for the ingestion schema.

    If the DB already has ingestion tables but no Alembic version table (legacy
    pre-Alembic init), we stamp head to avoid trying to recreate tables.
    """
    if not _ALEMBIC_CFG_PATH.exists():
        raise RuntimeError(f'Missing Alembic ingestion config: {_ALEMBIC_CFG_PATH}')

    cfg = _make_alembic_config(engine)

    with engine.connect() as connection:
        cfg.attributes['connection'] = connection

        inspector = inspect(connection)
        has_ingestion_tables = inspector.has_table('ingestion_jobs')
        has_alembic_version = inspector.has_table('alembic_version')

        current_revision = None
        if has_alembic_version:
            migration_context = MigrationContext.configure(connection)
            current_revision = migration_context.get_current_revision()

        # Legacy or partially initialized DB cases:
        # - ingestion tables already exist
        # - Alembic has no current revision (no table or empty version table)
        # In this state, stamp head before upgrade to avoid replaying initial DDL.
        if has_ingestion_tables and current_revision is None:
            command.stamp(cfg, _LEGACY_BASE_REVISION)

        command.upgrade(cfg, 'head')
