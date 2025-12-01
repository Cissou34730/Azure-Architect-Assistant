"""Synchronous database utilities for the ingestion pipeline."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.ingestion.models import Base

DATA_ROOT = Path(__file__).parent.parent / "data"
DATA_ROOT.mkdir(exist_ok=True)

INGESTION_DB_PATH = os.getenv(
    "INGESTION_DATABASE_PATH",
    str(DATA_ROOT / "ingestion.db"),
)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{INGESTION_DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_ingestion_database() -> None:
    """Ensure ingestion tables exist and migrations are applied."""
    from app.ingestion import migrations

    migrations.run_migrations(engine)


@contextmanager
def get_session() -> Iterator[Session]:
    """Provide a transactional session scope for ingestion operations."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
