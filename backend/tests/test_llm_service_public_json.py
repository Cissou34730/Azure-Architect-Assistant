"""Tests for the public LLMService.complete_json API."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.shared.ai.llm_service import LLMService


def _make_service() -> LLMService:
    service = LLMService.__new__(LLMService)
    service.ai_service = Mock()
    service.app_settings = Mock()
    service.app_settings.llm_request_timeout_seconds = 30
    service.app_settings.llm_response_preview_log_chars = 500
    return service


class TestCompleteJsonPublic:
    @pytest.mark.asyncio
    async def test_public_complete_json_delegates(self):
        service = _make_service()
        expected = {"answer": 42}
        service._complete_json = AsyncMock(return_value=expected)

        result = await service.complete_json("sys", "user", max_tokens=123)

        assert result == expected
        service._complete_json.assert_awaited_once_with("sys", "user", max_tokens=123)

    @pytest.mark.asyncio
    async def test_public_complete_json_default_max_tokens(self):
        service = _make_service()
        service._complete_json = AsyncMock(return_value={})

        await service.complete_json("sys", "user")

        service._complete_json.assert_awaited_once_with("sys", "user", max_tokens=2000)
