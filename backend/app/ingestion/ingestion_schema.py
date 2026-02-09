"""Schema migration utilities for ingestion tables."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine
from sqlalchemy import inspect

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_CFG_PATH = _BACKEND_ROOT / 'alembic_ingestion.ini'


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
        has_alembic_version = inspector.has_table('alembic_version')
        has_ingestion_tables = inspector.has_table('ingestion_jobs')

        if not has_alembic_version and has_ingestion_tables:
            command.stamp(cfg, 'head')

        command.upgrade(cfg, 'head')
