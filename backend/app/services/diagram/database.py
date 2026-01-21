"""Diagram database session factory and lifecycle management."""

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.app_settings import get_app_settings
from app.models.diagram import Base


class DiagramDatabase:
    """Manages diagram database engine and session factory."""

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def initialize(self) -> None:
        """
        Initialize diagram database engine and session factory.
        Creates the database file and tables if they don't exist.
        """
        settings = get_app_settings()

        # Build DSN from filesystem path and ensure directory exists
        db_file: Path = settings.diagrams_database
        db_file.parent.mkdir(parents=True, exist_ok=True)
        dsn = f"sqlite+aiosqlite:///{db_file.as_posix()}"

        # Create async engine
        self._engine = create_async_engine(
            dsn,
            echo=False,
            poolclass=NullPool,  # SQLite doesn't benefit from connection pooling
            connect_args={"check_same_thread": False},
        )

        # Create session factory
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Create all tables
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get diagram database session."""
        if self._session_factory is None:
            raise RuntimeError(
                "Diagram database not initialized. "
                "Call initialize() during application startup."
            )

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        """Close diagram database connections."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Global instance
_db_manager = DiagramDatabase()


async def init_diagram_database() -> None:
    """Entry point for initializing the diagram database."""
    await _db_manager.initialize()


async def get_diagram_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for diagram sessions."""
    async for session in _db_manager.get_session():
        yield session


async def close_diagram_database() -> None:
    """Cleanup module resources."""
    await _db_manager.close()

