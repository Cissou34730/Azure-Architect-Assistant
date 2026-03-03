"""Tests for ingestion router endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.projects_database import get_db
from app.routers.ingestion import (
    get_ingestion_runtime_service_dep,
    get_job_repository_dep,
)
from app.service_registry import get_kb_manager as sr_get_kb_manager


@pytest.fixture
async def async_client(test_db_session: AsyncSession, mock_kb_manager):
    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    # The ingestion router imports get_kb_manager from service_registry
    app.dependency_overrides[sr_get_kb_manager] = lambda: mock_kb_manager

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_start_ingestion_kb_not_found(async_client: AsyncClient, mock_kb_manager) -> None:
    mock_kb_manager.kb_exists.return_value = False
    response = await async_client.post("/api/ingestion/kb/nonexistent/start")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_start_ingestion_success(async_client: AsyncClient, mock_kb_manager) -> None:
    mock_kb_manager.kb_exists.return_value = True
    mock_kb_manager.get_kb_config.return_value = {
        "kb_id": "test-kb",
        "source_type": "website",
        "source_config": {"url": "https://example.com"},
    }

    mock_runtime_service = Mock()
    mock_runtime_service.start_ingestion = AsyncMock(
        return_value={
            "job_id": "job-123",
            "kb_id": "test-kb",
            "status": "running",
            "started_at": datetime.now(timezone.utc),
        }
    )
    app.dependency_overrides[get_ingestion_runtime_service_dep] = lambda: mock_runtime_service
    response = await async_client.post("/api/ingestion/kb/test-kb/start")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "job-123"
    assert data["kb_id"] == "test-kb"


@pytest.mark.asyncio
async def test_get_job_status(async_client: AsyncClient) -> None:
    mock_repo = Mock()
    mock_repo.get_job.return_value = Mock(
        id="job-123",
        kb_id="test-kb",
        status="running",
        counters={},
        checkpoint=None,
        last_error=None,
        created_at=datetime.now(timezone.utc),
        finished_at=None,
    )
    mock_repo.get_job_status.return_value = "running"
    app.dependency_overrides[get_job_repository_dep] = lambda: mock_repo
    response = await async_client.get("/api/ingestion/kb/job-123/status")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_pause_ingestion_no_job(async_client: AsyncClient) -> None:
    from fastapi import HTTPException  # noqa: PLC0415

    mock_runtime_service = Mock()
    mock_runtime_service.pause_ingestion = AsyncMock(
        side_effect=HTTPException(status_code=404, detail="No job found for KB 'test-kb'")
    )
    app.dependency_overrides[get_ingestion_runtime_service_dep] = lambda: mock_runtime_service
    response = await async_client.post("/api/ingestion/kb/test-kb/pause")
    assert response.status_code == 404
