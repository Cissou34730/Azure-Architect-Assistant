from __future__ import annotations

import sqlite3

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError

from app.ingestion import ingestion_schema
from app.ingestion.ingestion_schema import run_migrations


def test_run_migrations_creates_ingestion_tables(tmp_path) -> None:
    db_path = tmp_path / 'ingestion.db'
    engine = create_engine(f"sqlite:///{db_path}", future=True)

    run_migrations(engine)

    inspector = inspect(engine)
    assert inspector.has_table('ingestion_jobs')
    assert inspector.has_table('ingestion_phase_status')
    assert inspector.has_table('ingestion_queue') is False
    assert inspector.has_table('alembic_version')

    columns = {column['name'] for column in inspector.get_columns('ingestion_jobs')}
    assert 'current_phase' not in columns
    assert 'phase_progress' not in columns


def test_run_migrations_cleans_stale_alembic_temp_table(tmp_path) -> None:
    db_path = tmp_path / 'ingestion.db'
    engine = create_engine(f"sqlite:///{db_path}", future=True)

    run_migrations(engine)

    with engine.begin() as connection:
        connection.exec_driver_sql(
            'CREATE TABLE IF NOT EXISTS _alembic_tmp_ingestion_jobs (id TEXT PRIMARY KEY)'
        )

    run_migrations(engine)

    inspector = inspect(engine)
    assert inspector.has_table('_alembic_tmp_ingestion_jobs') is False


def test_upgrade_retries_once_on_stale_temp_table_collision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    db_path = tmp_path / 'ingestion.db'
    engine = create_engine(f"sqlite:///{db_path}", future=True)

    calls = {'count': 0}
    original_upgrade = ingestion_schema.command.upgrade

    def flaky_upgrade(cfg, revision):
        calls['count'] += 1
        if calls['count'] == 1:
            raise OperationalError(
                'CREATE TABLE _alembic_tmp_ingestion_jobs (...)',
                None,
                sqlite3.OperationalError('table _alembic_tmp_ingestion_jobs already exists'),
            )
        return original_upgrade(cfg, revision)

    monkeypatch.setattr(ingestion_schema.command, 'upgrade', flaky_upgrade)

    run_migrations(engine)

    assert calls['count'] == 2
