"""Tests for KB management router endpoints."""

from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_kb_manager
from app.main import app
from app.projects_database import get_db
from app.routers.kb_management.management_router import (
    get_management_service_dep,
)


@pytest.fixture
def mock_management_service():
    svc = Mock()
    svc.create_knowledge_base = Mock(return_value={
        "message": "KB created", "kb_id": "test-kb", "kb_name": "Test KB"
    })
    svc.list_knowledge_bases = Mock(return_value=[
        {"id": "kb-1", "name": "KB 1", "profiles": ["chat"], "priority": 1, "status": "ready"}
    ])
    svc.check_health = Mock(return_value={
        "overall_status": "healthy",
        "knowledge_bases": [
            {"kb_id": "kb-1", "kb_name": "KB 1", "status": "ready", "index_ready": True, "error": None}
        ],
    })
    svc.delete_knowledge_base = AsyncMock(
        return_value={
            "message": "Knowledge base 'test-kb' deleted successfully",
            "kb_id": "test-kb",
        }
    )
    return svc


@pytest.fixture
async def async_client(test_db_session: AsyncSession, mock_kb_manager, mock_management_service):
    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_kb_manager] = lambda: mock_kb_manager
    app.dependency_overrides[get_management_service_dep] = lambda: mock_management_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_knowledge_bases(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/kb/list")
    assert response.status_code == 200
    data = response.json()
    assert "knowledge_bases" in data
    assert len(data["knowledge_bases"]) == 1
    assert data["knowledge_bases"][0]["id"] == "kb-1"


@pytest.mark.asyncio
async def test_create_kb(async_client: AsyncClient) -> None:
    payload = {
        "kb_id": "test-kb",
        "name": "Test KB",
        "source_type": "website",
        "source_config": {"url": "https://example.com"},
    }
    response = await async_client.post("/api/kb/create", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["kb_id"] == "test-kb"


@pytest.mark.asyncio
async def test_delete_kb_not_found(async_client: AsyncClient, mock_kb_manager) -> None:
    from fastapi import HTTPException  # noqa: PLC0415

    get_management_service_dep_instance = app.dependency_overrides[get_management_service_dep]()
    get_management_service_dep_instance.delete_knowledge_base = AsyncMock(
        side_effect=HTTPException(status_code=404, detail="Knowledge base 'nonexistent' not found")
    )
    response = await async_client.delete("/api/kb/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_kb_success(async_client: AsyncClient, mock_kb_manager) -> None:
    response = await async_client.delete("/api/kb/test-kb")

    assert response.status_code == 200
    data = response.json()
    assert data["kb_id"] == "test-kb"


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/kb/health")
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "healthy"
    assert len(data["knowledge_bases"]) == 1
