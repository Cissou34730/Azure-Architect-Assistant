"""Tests for diagram generation router endpoints."""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.diagram import Base as DiagramBase
from app.projects_database import get_db
from app.services.diagram.database import get_diagram_session


@pytest_asyncio.fixture
async def diagram_db_session():
    """Create an in-memory DB with diagram tables."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(DiagramBase.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def async_client(diagram_db_session: AsyncSession):
    async def override_diagram_session():
        yield diagram_db_session

    app.dependency_overrides[get_diagram_session] = override_diagram_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_diagram_set_validation(async_client: AsyncClient) -> None:
    # Too short description
    response = await async_client.post(
        "/api/diagram-sets",
        json={"input_description": "short"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_diagram_set_not_found(async_client: AsyncClient) -> None:
    fake_id = str(uuid.uuid4())
    response = await async_client.get(f"/api/diagram-sets/{fake_id}")
    assert response.status_code == 404
