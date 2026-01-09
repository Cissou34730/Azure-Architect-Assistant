"""Synchronous database utilities for the ingestion pipeline."""

from __future__ import annotations

import os
from app.core.config import get_app_settings
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


# Point to consolidated data directory at backend/data
BACKEND_ROOT = Path(__file__).parent.parent.parent
DATA_ROOT = BACKEND_ROOT / "data"
DATA_ROOT.mkdir(exist_ok=True)

app_settings = None
try:
    app_settings = get_app_settings()
except Exception:
    app_settings = None

if app_settings and app_settings.ingestion_database:
    INGESTION_DB_PATH = str(app_settings.ingestion_database)
else:
    INGESTION_DB_PATH = os.getenv(
        "INGESTION_DATABASE",
        str(DATA_ROOT / "ingestion.db"),
    )

# Handle relative paths
if not Path(INGESTION_DB_PATH).is_absolute():
    INGESTION_DB_PATH = str(BACKEND_ROOT / INGESTION_DB_PATH)

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
    from app.ingestion import ingestion_schema

    ingestion_schema.run_migrations(engine)


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
