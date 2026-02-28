"""Tests for KB query router endpoints."""

from unittest.mock import Mock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_kb_manager
from app.main import app
from app.projects_database import get_db
from app.routers.kb_query.query_router import (
    get_multi_query_service_dep,
    get_query_service_dep,
)


@pytest.fixture
def mock_query_service():
    svc = Mock()
    svc.query_with_profile = Mock(return_value={
        "answer": "Test answer",
        "sources": [{"url": "https://example.com", "title": "Example", "section": "s1", "score": 0.9}],
        "has_results": True,
        "suggested_follow_ups": [],
    })
    return svc


@pytest.fixture
def mock_multi_query_service():
    return Mock()


@pytest.fixture
async def async_client(
    test_db_session: AsyncSession,
    mock_kb_manager,
    mock_query_service,
    mock_multi_query_service,
):
    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_kb_manager] = lambda: mock_kb_manager
    app.dependency_overrides[get_query_service_dep] = lambda: mock_query_service
    app.dependency_overrides[get_multi_query_service_dep] = lambda: mock_multi_query_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_legacy_query(async_client: AsyncClient, mock_query_service) -> None:
    response = await async_client.post("/api/query", json={"question": "What is WAF?"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["answer"] == "Test answer"


@pytest.mark.asyncio
async def test_legacy_query_missing_question(async_client: AsyncClient) -> None:
    response = await async_client.post("/api/query", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_query(async_client: AsyncClient, mock_kb_manager, mock_query_service) -> None:
    mock_kb_manager.get_kbs_for_profile.return_value = []
    response = await async_client.post(
        "/api/query/chat",
        json={"question": "Tell me about reliability"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
