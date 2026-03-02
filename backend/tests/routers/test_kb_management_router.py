"""Tests for KB management router endpoints."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_kb_manager
from app.main import app
from app.projects_database import get_db
from app.routers.kb_management.management_router import (
    get_management_service_dep,
    get_multi_query_service_dep,
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
    return svc


@pytest.fixture
async def async_client(test_db_session: AsyncSession, mock_kb_manager, mock_management_service):
    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_kb_manager] = lambda: mock_kb_manager
    app.dependency_overrides[get_management_service_dep] = lambda: mock_management_service
    app.dependency_overrides[get_multi_query_service_dep] = lambda: Mock()

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
    with patch("app.routers.kb_management.management_router.invalidate_kb_manager"):
        response = await async_client.post("/api/kb/create", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["kb_id"] == "test-kb"


@pytest.mark.asyncio
async def test_delete_kb_not_found(async_client: AsyncClient, mock_kb_manager) -> None:
    mock_kb_manager.kb_exists.return_value = False
    response = await async_client.delete("/api/kb/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_kb_success(async_client: AsyncClient, mock_kb_manager) -> None:
    mock_kb_manager.kb_exists.return_value = True
    mock_kb_manager.get_kb.return_value = Mock(index_path="/tmp/test")

    with (
        patch("app.routers.kb_management.management_router.create_job_repository") as mock_repo_factory,
        patch("app.routers.kb_management.management_router.clear_index_cache"),
        patch("app.routers.kb_management.management_router.invalidate_kb_manager"),
    ):
        mock_repo = Mock()
        mock_repo.get_latest_job_id.return_value = None
        mock_repo_factory.return_value = mock_repo
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
