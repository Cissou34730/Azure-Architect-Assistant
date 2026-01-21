"""
Database helper functions.
Central place to obtain project (async) and ingestion (sync) sessions.
"""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.ingestion_database import get_session as _get_ingestion_session
from app.projects_database import AsyncSessionLocal


@asynccontextmanager
async def get_project_session() -> AsyncIterator[AsyncSession]:
    """
    Async project DB session helper (wraps AsyncSessionLocal).
    Intended for FastAPI Depends usage.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@contextmanager
def get_ingestion_session() -> Iterator:
    """
    Sync ingestion DB session helper (wraps ingestion SessionLocal).
    """
    with _get_ingestion_session() as session:  # type: ignore[misc]
        yield session

