from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.shared.ai.llm_service import LLMService


@pytest.mark.asyncio
async def test_complete_json_uses_model_default_temperature(monkeypatch: pytest.MonkeyPatch) -> None:
    chat = AsyncMock(return_value=SimpleNamespace(content='{"ok": true}'))
    ai_service = SimpleNamespace(
        chat=chat,
        config=SimpleNamespace(default_temperature=0.7),
        get_llm_model=lambda: "gpt-5.3-chat",
    )
    settings = SimpleNamespace(
        llm_request_timeout_seconds=30,
        llm_response_preview_log_chars=200,
        llm_json_repair_min_tokens=100,
        llm_json_repair_token_divisor=2,
        llm_response_error_log_chars=200,
    )

    monkeypatch.setattr("app.shared.ai.llm_service.get_ai_service", lambda: ai_service)
    monkeypatch.setattr("app.shared.ai.llm_service.get_app_settings", lambda: settings)

    service = LLMService()

    result = await service._complete_json("system", "user", max_tokens=123)

    assert result == {"ok": True}
    call_kwargs = chat.await_args.kwargs
    assert call_kwargs["max_tokens"] == 123
    assert call_kwargs["response_format"] == {"type": "json_object"}
    assert call_kwargs["use_model_default_temperature"] is True
    assert call_kwargs["temperature"] is None
