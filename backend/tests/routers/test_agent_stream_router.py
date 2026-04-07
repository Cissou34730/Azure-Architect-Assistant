"""Tests for agent streaming router endpoints."""

from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.shared.db.projects_database import get_db


@pytest.fixture
async def async_client(test_db_session: AsyncSession):
    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_project_chat_stream_endpoint(async_client: AsyncClient) -> None:
    async def _fake_stream(*_args, **_kwargs) -> AsyncIterator[str]:
        yield 'event: message_start\ndata: {"role":"assistant"}\n\n'
        yield (
            'event: final\ndata: {"answer":"streamed","success":true,'
            '"project_state":{"projectId":"p1"},"reasoning_steps":[],"error":null}\n\n'
        )

    with patch(
        "app.features.agent.application.agent_api_service.AgentApiService.project_chat_stream",
        _fake_stream,
    ):
        response = await async_client.post(
            "/api/agent/projects/p1/chat/stream",
            json={"message": "hello"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'event: message_start' in response.text
    assert 'event: final' in response.text
