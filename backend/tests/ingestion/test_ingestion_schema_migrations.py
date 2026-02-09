from __future__ import annotations

from sqlalchemy import create_engine, inspect

from app.ingestion.ingestion_schema import run_migrations


def test_run_migrations_creates_ingestion_tables(tmp_path) -> None:
    db_path = tmp_path / 'ingestion.db'
    engine = create_engine(f"sqlite:///{db_path}", future=True)

    run_migrations(engine)

    inspector = inspect(engine)
    assert inspector.has_table('ingestion_jobs')
    assert inspector.has_table('ingestion_phase_status')
    assert inspector.has_table('ingestion_queue')
    assert inspector.has_table('alembic_version')
