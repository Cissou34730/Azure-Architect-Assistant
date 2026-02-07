"""
Global pytest fixtures for backend tests.
"""

import asyncio
from typing import AsyncGenerator
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.project import Base
from app.core.app_settings import get_settings
from app.agents_system.checklists.registry import ChecklistRegistry
from app.agents_system.checklists.engine import ChecklistEngine
from app.agents_system.checklists.service import ChecklistService
from app.models.checklist import ChecklistTemplate


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an in-memory database and provide an async session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with session_factory() as session:
        yield session
        
    await engine.dispose()


@pytest.fixture
def mock_settings():
    """Provide mock settings."""
    settings = get_settings()
    # Override settings for testing if needed
    return settings


@pytest.fixture
def test_registry(mock_settings, tmp_path):
    """Provide a registry with a temporary cache directory."""
    cache_dir = tmp_path / "checklists"
    cache_dir.mkdir()
    registry = ChecklistRegistry(cache_dir=cache_dir, settings=mock_settings)
    registry.register_template(
        ChecklistTemplate(
            slug="azure-waf-v1",
            title="Azure WAF",
            description="Test template",
            version="1.0",
            source="tests",
            source_url="https://example.com",
            source_version="1.0",
            content={
                "items": [
                    {
                        "id": "sec-01",
                        "title": "Secure Admin Access",
                        "pillar": "Security",
                        "severity": "high",
                    },
                    {
                        "id": "rel-01",
                        "title": "Backup Strategy",
                        "pillar": "Reliability",
                        "severity": "critical",
                    },
                ]
            },
        )
    )
    return registry


@pytest.fixture
def test_engine(test_db_session, test_registry, mock_settings):
    """Provide a ChecklistEngine with the test database."""
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def session_factory():
        yield test_db_session
        
    return ChecklistEngine(
        db_session_factory=session_factory,
        registry=test_registry,
        settings=mock_settings
    )


@pytest.fixture
def test_checklist_service(test_engine, test_registry):
    """Provide a ChecklistService."""
    return ChecklistService(engine=test_engine, registry=test_registry)
