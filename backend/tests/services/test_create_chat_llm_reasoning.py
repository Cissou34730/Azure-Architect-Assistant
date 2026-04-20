"""ModelCapabilityCache, create_chat_llm integration, and agent-level retry."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.shared.ai.ai_service import AIService
from app.shared.ai.config import AIConfig
from app.shared.ai.model_capability_cache import ModelCapabilityCache


# ── ModelCapabilityCache unit tests ──────────────────────────────────────────


class TestModelCapabilityCache:
    def setup_method(self) -> None:
        ModelCapabilityCache.reset()

    def teardown_method(self) -> None:
        ModelCapabilityCache.reset()

    def test_singleton_returns_same_instance(self) -> None:
        a = ModelCapabilityCache.instance()
        b = ModelCapabilityCache.instance()
        assert a is b

    def test_reset_clears_singleton(self) -> None:
        a = ModelCapabilityCache.instance()
        ModelCapabilityCache.reset()
        b = ModelCapabilityCache.instance()
        assert a is not b

    def test_param_supported_by_default(self) -> None:
        cache = ModelCapabilityCache.instance()
        assert cache.is_supported("openai", "gpt-5.3", "temperature") is True

    def test_mark_unsupported_then_query(self) -> None:
        cache = ModelCapabilityCache.instance()
        cache.mark_unsupported("openai", "gpt-5.3", "temperature")
        assert cache.is_supported("openai", "gpt-5.3", "temperature") is False
        # Other params still supported
        assert cache.is_supported("openai", "gpt-5.3", "max_tokens") is True

    def test_different_provider_same_model_independent(self) -> None:
        cache = ModelCapabilityCache.instance()
        cache.mark_unsupported("openai", "o3", "temperature")
        assert cache.is_supported("openai", "o3", "temperature") is False
        assert cache.is_supported("foundry", "o3", "temperature") is True

    def test_get_unsupported_returns_frozenset(self) -> None:
        cache = ModelCapabilityCache.instance()
        cache.mark_unsupported("openai", "gpt-5.3", "temperature")
        cache.mark_unsupported("openai", "gpt-5.3", "response_format")
        result = cache.get_unsupported("openai", "gpt-5.3")
        assert result == frozenset({"temperature", "response_format"})
        assert isinstance(result, frozenset)

    def test_get_unsupported_empty_for_unknown_model(self) -> None:
        cache = ModelCapabilityCache.instance()
        assert cache.get_unsupported("openai", "unknown") == frozenset()


class TestExtractRejectedParam:
    """Test the error-parsing logic for various error shapes."""

    def test_structured_openai_sdk_error(self) -> None:
        """OpenAI SDK BadRequestError with .param and .code attributes."""
        error = Exception("some message")
        error.param = "temperature"  # type: ignore[attr-defined]
        error.code = "unsupported_value"  # type: ignore[attr-defined]
        assert ModelCapabilityCache.extract_rejected_param(error) == "temperature"

    def test_structured_body_dict(self) -> None:
        """Error with .body dict containing nested error object."""
        error = Exception("some message")
        error.body = {  # type: ignore[attr-defined]
            "error": {
                "param": "response_format",
                "code": "unsupported_value",
            }
        }
        assert ModelCapabilityCache.extract_rejected_param(error) == "response_format"

    def test_regex_fallback(self) -> None:
        """When structured fields are absent, fall back to regex."""
        error = Exception(
            "Unsupported value: 'temperature' does not support 0.1 with this model."
        )
        assert ModelCapabilityCache.extract_rejected_param(error) == "temperature"

    def test_regex_max_tokens(self) -> None:
        error = Exception("'max_tokens' is not supported with this model.")
        assert ModelCapabilityCache.extract_rejected_param(error) == "max_tokens"

    def test_non_param_error_returns_none(self) -> None:
        error = RuntimeError("Something else broke")
        assert ModelCapabilityCache.extract_rejected_param(error) is None

    def test_wrong_code_not_extracted(self) -> None:
        """Structured param present but code is not unsupported_value."""
        error = Exception("invalid")
        error.param = "temperature"  # type: ignore[attr-defined]
        error.code = "invalid_type"  # type: ignore[attr-defined]
        assert ModelCapabilityCache.extract_rejected_param(error) is None


# ── create_chat_llm: proactive cache integration ────────────────────────────


class TestCreateChatLlmCacheIntegration:
    def setup_method(self) -> None:
        ModelCapabilityCache.reset()

    def teardown_method(self) -> None:
        ModelCapabilityCache.reset()

    def test_passes_temperature_when_model_unknown(self) -> None:
        """First call to an unknown model includes temperature."""
        config = AIConfig(
            llm_provider="openai",
            openai_api_key="sk-test",
            openai_llm_model="gpt-5.3",
        )
        svc = AIService.__new__(AIService)
        svc.config = config

        with patch("langchain_openai.ChatOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            svc.create_chat_llm(temperature=0.1)

        _, call_kwargs = mock_cls.call_args
        assert call_kwargs["temperature"] == 0.1

    def test_omits_temperature_when_cached_unsupported(self) -> None:
        """After cache marks temperature unsupported, create_chat_llm omits it."""
        cache = ModelCapabilityCache.instance()
        cache.mark_unsupported("openai", "gpt-5.3", "temperature")

        config = AIConfig(
            llm_provider="openai",
            openai_api_key="sk-test",
            openai_llm_model="gpt-5.3",
        )
        svc = AIService.__new__(AIService)
        svc.config = config

        with patch("langchain_openai.ChatOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            svc.create_chat_llm(temperature=0.1)

        _, call_kwargs = mock_cls.call_args
        assert "temperature" not in call_kwargs

    def test_omits_temperature_foundry_cached(self) -> None:
        """Foundry provider also respects the cache."""
        cache = ModelCapabilityCache.instance()
        cache.mark_unsupported("foundry", "o4-mini", "temperature")

        config = AIConfig(
            llm_provider="foundry",
            foundry_endpoint="https://test.openai.azure.com",
            foundry_api_key="key-test",
            foundry_model="o4-mini",
        )
        svc = AIService.__new__(AIService)
        svc.config = config

        with patch("langchain_openai.AzureChatOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            svc.create_chat_llm(temperature=0.1)

        _, call_kwargs = mock_cls.call_args
        assert "temperature" not in call_kwargs

    def test_other_model_unaffected(self) -> None:
        """Caching for one model doesn't affect another."""
        cache = ModelCapabilityCache.instance()
        cache.mark_unsupported("openai", "gpt-5.3", "temperature")

        config = AIConfig(
            llm_provider="openai",
            openai_api_key="sk-test",
            openai_llm_model="gpt-4o",
        )
        svc = AIService.__new__(AIService)
        svc.config = config

        with patch("langchain_openai.ChatOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            svc.create_chat_llm(temperature=0.1)

        _, call_kwargs = mock_cls.call_args
        assert call_kwargs["temperature"] == 0.1


# ── agent-level retry on parameter rejection ────────────────────────────────


def _build_agent_state() -> dict:
    return {
        "user_message": "update requirements",
        "next_stage": "general",
        "project_id": "p1",
        "stage_directives": "",
        "context_pack": "",
        "research_plan": [],
        "grounded_evidence": [],
        "mindmap_guidance": "",
        "db": None,
        "user_message_id": None,
        "event_callback": None,
    }


@pytest.mark.asyncio
async def test_agent_retries_on_param_rejection_and_caches() -> None:
    """run_stage_aware_agent catches unsupported-param errors, populates
    the cache, recreates the LLM, and retries successfully."""
    from app.agents_system.langgraph.nodes.agent_native import run_stage_aware_agent

    ModelCapabilityCache.reset()
    fake_result = {"agent_output": "ok", "tool_outputs": []}
    call_count = 0

    async def _fake_dispatch(*, llm, base_llm, tools, agent_initial_state, event_callback):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            exc = Exception(
                "Unsupported value: 'temperature' does not support 0.1 with this model."
            )
            exc.param = "temperature"  # type: ignore[attr-defined]
            exc.code = "unsupported_value"  # type: ignore[attr-defined]
            raise exc
        return fake_result

    mock_ai_service = MagicMock()
    mock_llm = MagicMock()
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)

    create_calls: list[dict] = []

    def _track_create(*, temperature=None, **kw):
        create_calls.append({"temperature": temperature})
        return mock_llm

    mock_ai_service.create_chat_llm = _track_create
    mock_ai_service.config = AIConfig(
        llm_provider="openai",
        openai_api_key="sk-test",
        openai_llm_model="gpt-5.3",
    )

    mock_settings = MagicMock()
    mock_settings.chat_temperature = 0.1

    with (
        patch(
            "app.agents_system.langgraph.nodes.agent_native.get_ai_service",
            return_value=mock_ai_service,
        ),
        patch(
            "app.agents_system.langgraph.nodes.agent_native.get_app_settings",
            return_value=mock_settings,
        ),
        patch(
            "app.agents_system.langgraph.nodes.agent_native._build_tools",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.agents_system.langgraph.nodes.agent_native._build_system_directives",
            return_value="sys",
        ),
        patch(
            "app.agents_system.langgraph.nodes.agent_native._dispatch_agent",
            side_effect=_fake_dispatch,
        ),
    ):
        result = await run_stage_aware_agent(
            _build_agent_state(),
            mcp_client=MagicMock(),
            openai_settings=None,
        )

    assert result == fake_result
    assert call_count == 2
    assert create_calls[0]["temperature"] == 0.1
    # Second call uses the configured temperature again — but create_chat_llm
    # will now consult the cache and proactively strip it.
    assert create_calls[1]["temperature"] == 0.1

    # Verify cache was populated
    cache = ModelCapabilityCache.instance()
    assert cache.is_supported("openai", "gpt-5.3", "temperature") is False
    ModelCapabilityCache.reset()


@pytest.mark.asyncio
async def test_agent_does_not_retry_on_non_param_error() -> None:
    """Non-parameter errors propagate without retry."""
    from app.agents_system.langgraph.nodes.agent_native import run_stage_aware_agent

    ModelCapabilityCache.reset()

    async def _fake_dispatch(*, llm, base_llm, tools, agent_initial_state, event_callback):
        raise RuntimeError("Something else broke")

    mock_ai_service = MagicMock()
    mock_llm = MagicMock()
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)
    mock_ai_service.create_chat_llm = MagicMock(return_value=mock_llm)
    mock_ai_service.config = AIConfig(
        llm_provider="openai",
        openai_api_key="sk-test",
        openai_llm_model="gpt-5.3",
    )

    mock_settings = MagicMock()
    mock_settings.chat_temperature = 0.1

    with (
        patch(
            "app.agents_system.langgraph.nodes.agent_native.get_ai_service",
            return_value=mock_ai_service,
        ),
        patch(
            "app.agents_system.langgraph.nodes.agent_native.get_app_settings",
            return_value=mock_settings,
        ),
        patch(
            "app.agents_system.langgraph.nodes.agent_native._build_tools",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.agents_system.langgraph.nodes.agent_native._build_system_directives",
            return_value="sys",
        ),
        patch(
            "app.agents_system.langgraph.nodes.agent_native._dispatch_agent",
            side_effect=_fake_dispatch,
        ),
    ):
        with pytest.raises(RuntimeError, match="Something else broke"):
            await run_stage_aware_agent(
                _build_agent_state(),
                mcp_client=MagicMock(),
                openai_settings=None,
            )

    ModelCapabilityCache.reset()
