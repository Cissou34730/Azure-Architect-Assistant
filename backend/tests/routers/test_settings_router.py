"""Tests for settings/models router endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.shared.db.projects_database import get_db
from app.features.settings.api.models_router import _settings_models_service


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
async def test_get_available_models(async_client: AsyncClient) -> None:
    mock_model = Mock()
    mock_model.id = "gpt-4o"
    mock_model.name = "GPT-4o"
    mock_model.context_window = 128000
    mock_model.pricing = None

    with patch("app.features.settings.application.settings_service.ModelsService") as MockService:
        instance = MockService.return_value
        instance.get_available_models = AsyncMock(
            return_value=([mock_model], datetime.now(timezone.utc))
        )
        response = await async_client.get("/api/settings/available-models")

    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert len(data["models"]) == 1
    assert data["models"][0]["id"] == "gpt-4o"


@pytest.mark.asyncio
async def test_get_current_model(async_client: AsyncClient) -> None:
    mock_manager = Mock()
    mock_instance = Mock()
    mock_instance.get_llm_model.return_value = "gpt-4o-mini"
    mock_manager.get_instance.return_value = mock_instance

    with patch("app.features.settings.application.settings_service.AIServiceManager", mock_manager):
        response = await async_client.get("/api/settings/current-model")

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_get_llm_options(async_client: AsyncClient) -> None:
    payload = {
        "active_provider": "foundry",
        "active_model": "gpt-5.3-chat",
        "providers": [
            {
                "id": "foundry",
                "name": "Azure AI Foundry",
                "status": "ready",
                "status_message": None,
                "selected": True,
                "models": [
                    {
                        "id": "gpt-5.3-chat",
                        "name": "GPT-5.3 Chat",
                        "context_window": 200000,
                        "pricing": None,
                    }
                ],
                "auth": None,
            }
        ],
    }

    with patch.object(
        _settings_models_service,
        "get_llm_options",
        AsyncMock(return_value=payload),
    ):
        response = await async_client.get("/api/settings/llm-options")

    assert response.status_code == 200
    data = response.json()
    assert data["active_provider"] == "foundry"
    assert data["providers"][0]["id"] == "foundry"


@pytest.mark.asyncio
async def test_get_copilot_status(async_client: AsyncClient) -> None:
    payload = {
        "available": True,
        "authenticated": False,
        "state": "unauthenticated",
        "login": None,
        "auth_type": None,
        "host": None,
        "status_message": "Login required",
        "cli_path": "copilot",
        "quota": None,
    }

    with patch.object(
        _settings_models_service,
        "get_copilot_status",
        AsyncMock(return_value=payload),
    ):
        response = await async_client.get("/api/settings/copilot/status")

    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "unauthenticated"
