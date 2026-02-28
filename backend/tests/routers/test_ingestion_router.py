"""Tests for ingestion router endpoints."""

from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.projects_database import get_db
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

    with patch("app.routers.ingestion.repo") as mock_repo:
        mock_repo.create_job.return_value = "job-123"
        with patch("app.routers.ingestion.asyncio") as mock_asyncio:
            mock_task = Mock()
            mock_asyncio.create_task.return_value = mock_task
            response = await async_client.post("/api/ingestion/kb/test-kb/start")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "job-123"
    assert data["kb_id"] == "test-kb"


@pytest.mark.asyncio
async def test_get_job_status(async_client: AsyncClient) -> None:
    with patch("app.routers.ingestion.repo") as mock_repo:
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
        response = await async_client.get("/api/ingestion/kb/job-123/status")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_pause_ingestion_no_job(async_client: AsyncClient) -> None:
    with patch("app.routers.ingestion.repo") as mock_repo:
        mock_repo.get_latest_job_id.return_value = None
        response = await async_client.post("/api/ingestion/kb/test-kb/pause")
    assert response.status_code == 404
