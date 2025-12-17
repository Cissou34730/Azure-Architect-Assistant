"""Diagram database session factory and lifecycle management."""

from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_app_settings
from app.models.diagram import Base

# Global engine and session factory
_diagram_engine = None
_diagram_session_factory = None


def init_diagram_database() -> None:
    """
    Initialize diagram database engine and session factory.
    
    Call this during application startup.
    Creates the database file if it doesn't exist.
    """
    global _diagram_engine, _diagram_session_factory
    
    settings = get_app_settings()
    
    # Ensure data directory exists
    db_path = Path("backend/data")
    db_path.mkdir(parents=True, exist_ok=True)
    
    # Create async engine
    _diagram_engine = create_async_engine(
        settings.diagrams_database,
        echo=False,
        poolclass=NullPool,  # SQLite doesn't benefit from connection pooling
        connect_args={"check_same_thread": False},
    )
    
    # Create session factory
    _diagram_session_factory = async_sessionmaker(
        _diagram_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_diagram_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get diagram database session.
    
    Use as a dependency in FastAPI endpoints:
    ```python
    async def endpoint(session: AsyncSession = Depends(get_diagram_session)):
        ...
    ```
    
    Yields:
        AsyncSession: Database session
        
    Raises:
        RuntimeError: If database not initialized
    """
    if _diagram_session_factory is None:
        raise RuntimeError(
            "Diagram database not initialized. "
            "Call init_diagram_database() during application startup."
        )
    
    async with _diagram_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_diagram_database() -> None:
    """
    Close diagram database connections.
    
    Call this during application shutdown.
    """
    global _diagram_engine
    
    if _diagram_engine is not None:
        await _diagram_engine.dispose()
        _diagram_engine = None
