from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from app.shared.ai.ai_service import AIService
from app.shared.ai.config import AIConfig
from app.shared.ai.interfaces import ChatMessage
from app.shared.ai.providers.copilot_llm import CopilotLLMProvider


class _FakeRuntime:
    async def send_message(self, *, prompt, model, system_message, timeout):
        assert "USER: hello" in prompt
        assert model == "gpt-5.2"
        assert system_message == "You are helpful"
        assert timeout == 45.0
        return "copilot reply"

    async def list_models(self):
        return [_FakeModelInfo(id="gpt-5.2", name="GPT-5.2")]


@dataclass
class _FakeModelInfo:
    """Minimal stand-in for copilot.types.ModelInfo."""

    id: str
    name: str


class _FakeRuntimeWithModels:
    """Fake runtime that returns a fixed model list from list_models()."""

    def __init__(self, models: list[_FakeModelInfo]) -> None:
        self._models = models

    async def list_models(self) -> list[_FakeModelInfo]:
        return self._models


# ── SDK-based model discovery ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_copilot_provider_chat_and_list_models(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AIConfig(
        llm_provider="copilot",
        embedding_provider="openai",
        openai_api_key="test-openai-key",
        copilot_default_model="gpt-5.2",
        copilot_token="ghp_test_token_123",
        copilot_request_timeout=45.0,
    )
    provider = CopilotLLMProvider(config)

    monkeypatch.setattr(
        "app.shared.ai.providers.copilot_llm.get_copilot_runtime",
        AsyncMock(return_value=_FakeRuntime()),
    )

    response = await provider.chat(
        [
            ChatMessage(role="system", content="You are helpful"),
            ChatMessage(role="user", content="hello"),
        ]
    )
    models = await provider.list_runtime_models()

    assert response.content == "copilot reply"
    assert response.model == "gpt-5.2"
    # SDK model IDs are Copilot-specific names (not publisher-prefixed)
    assert models == [
        {"id": "gpt-5.2", "model": "gpt-5.2", "name": "GPT-5.2"},
    ]


@pytest.mark.asyncio
async def test_copilot_provider_lists_sdk_models_sorted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SDK models are returned sorted by id."""
    config = AIConfig(
        llm_provider="copilot",
        embedding_provider="openai",
        openai_api_key="test-openai-key",
        copilot_default_model="gpt-5.2",
        copilot_token="ghp_test_token_123",
    )
    provider = CopilotLLMProvider(config)

    fake_runtime = _FakeRuntimeWithModels([
        _FakeModelInfo(id="gpt-5.2", name="GPT-5.2"),
        _FakeModelInfo(id="claude-sonnet-4.6", name="Claude Sonnet 4.6"),
        _FakeModelInfo(id="gpt-5-mini", name="GPT-5 mini"),
        _FakeModelInfo(id="claude-opus-4.6", name="Claude Opus 4.6"),
    ])

    monkeypatch.setattr(
        "app.shared.ai.providers.copilot_llm.get_copilot_runtime",
        AsyncMock(return_value=fake_runtime),
    )

    models = await provider.list_runtime_models()

    assert models == [
        {"id": "claude-opus-4.6", "model": "claude-opus-4.6", "name": "Claude Opus 4.6"},
        {"id": "claude-sonnet-4.6", "model": "claude-sonnet-4.6", "name": "Claude Sonnet 4.6"},
        {"id": "gpt-5-mini", "model": "gpt-5-mini", "name": "GPT-5 mini"},
        {"id": "gpt-5.2", "model": "gpt-5.2", "name": "GPT-5.2"},
    ]


@pytest.mark.asyncio
async def test_copilot_provider_sdk_failure_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When SDK list_models() errors, fallback to configured allowlist."""
    config = AIConfig(
        llm_provider="copilot",
        embedding_provider="openai",
        openai_api_key="test-openai-key",
        copilot_default_model="gpt-5.2",
        copilot_token="ghp_test_token_123",
        copilot_allowed_models="gpt-5.2,gpt-5-mini",
    )
    provider = CopilotLLMProvider(config)

    async def _failing_runtime(_config):
        raise RuntimeError("Copilot is not authenticated")

    monkeypatch.setattr(
        "app.shared.ai.providers.copilot_llm.get_copilot_runtime",
        _failing_runtime,
    )

    models = await provider.list_runtime_models()

    assert models == [
        {"id": "gpt-5.2", "model": "gpt-5.2", "name": "gpt-5.2"},
        {"id": "gpt-5-mini", "model": "gpt-5-mini", "name": "gpt-5-mini"},
    ]


@pytest.mark.asyncio
async def test_copilot_provider_empty_sdk_list_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When SDK returns empty list, fallback to configured allowlist."""
    config = AIConfig(
        llm_provider="copilot",
        embedding_provider="openai",
        openai_api_key="test-openai-key",
        copilot_default_model="gpt-5.2",
        copilot_token="ghp_test_token_123",
        copilot_allowed_models="gpt-5.2",
    )
    provider = CopilotLLMProvider(config)

    fake_runtime = _FakeRuntimeWithModels([])

    monkeypatch.setattr(
        "app.shared.ai.providers.copilot_llm.get_copilot_runtime",
        AsyncMock(return_value=fake_runtime),
    )

    models = await provider.list_runtime_models()

    assert models == [
        {"id": "gpt-5.2", "model": "gpt-5.2", "name": "gpt-5.2"},
    ]


@pytest.mark.asyncio
async def test_copilot_provider_sdk_list_models_exception_in_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When runtime.list_models() raises, fallback to configured allowlist."""
    config = AIConfig(
        llm_provider="copilot",
        embedding_provider="openai",
        openai_api_key="test-openai-key",
        copilot_default_model="gpt-5.2",
        copilot_token="ghp_test_token_123",
        copilot_allowed_models="gpt-5.2,claude-sonnet-4.6",
    )
    provider = CopilotLLMProvider(config)

    fake_runtime = AsyncMock()
    fake_runtime.list_models = AsyncMock(side_effect=RuntimeError("not authenticated"))

    monkeypatch.setattr(
        "app.shared.ai.providers.copilot_llm.get_copilot_runtime",
        AsyncMock(return_value=fake_runtime),
    )

    models = await provider.list_runtime_models()

    assert models == [
        {"id": "gpt-5.2", "model": "gpt-5.2", "name": "gpt-5.2"},
        {"id": "claude-sonnet-4.6", "model": "claude-sonnet-4.6", "name": "claude-sonnet-4.6"},
    ]


# ── AIService integration ────────────────────────────────────────────


def test_ai_service_builds_copilot_provider() -> None:
    config = AIConfig(
        llm_provider="copilot",
        embedding_provider="openai",
        openai_api_key="test-openai-key",
        copilot_default_model="gpt-5.2",
        copilot_token="ghp_test_token_123",
    )

    service = AIService(config)

    assert isinstance(service._llm_provider, CopilotLLMProvider)


def test_ai_service_builds_copilot_chat_model() -> None:
    """create_chat_llm() returns a CopilotChatModel backed by the SDK."""
    from app.shared.ai.providers.copilot_chat_model import CopilotChatModel

    config = AIConfig(
        llm_provider="copilot",
        embedding_provider="openai",
        openai_api_key="test-openai-key",
        copilot_default_model="claude-sonnet-4.6",
        copilot_token="ghp_test_token_123",
    )

    service = AIService(config)
    chat_llm = service.create_chat_llm(temperature=0.15)

    assert isinstance(chat_llm, CopilotChatModel)
    assert chat_llm.model_name == "claude-sonnet-4.6"


def test_copilot_chat_model_supports_bind_tools() -> None:
    """CopilotChatModel supports native tool binding for agent pipelines."""

    config = AIConfig(
        llm_provider="copilot",
        embedding_provider="openai",
        openai_api_key="test-openai-key",
        copilot_default_model="claude-sonnet-4.6",
        copilot_token="ghp_test_token_123",
    )

    service = AIService(config)
    chat_llm = service.create_chat_llm(temperature=0.5)

    dummy_tools = [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "Search for information",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        }
    ]
    bound = chat_llm.bind_tools(dummy_tools)
    assert bound is not None


# ── Token / config tests ─────────────────────────────────────────────


def test_copilot_validation_succeeds_without_token() -> None:
    """Copilot provider validation passes without a token (SDK uses CLI auth)."""
    config = AIConfig(
        llm_provider="copilot",
        embedding_provider="openai",
        openai_api_key="test-openai-key",
        copilot_default_model="gpt-4o",
        copilot_token="",
    )
    # Should NOT raise — SDK handles auth via CLI, token is optional
    config.validate_provider_config()


def test_copilot_config_from_settings_includes_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """AIConfig.from_settings picks up the copilot token from AppSettings."""
    monkeypatch.setenv("AI_LLM_PROVIDER", "copilot")
    monkeypatch.setenv("AI_COPILOT_TOKEN", "ghp_from_env_test")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.shared.config.app_settings._read_secretkeeper_secret", lambda _key: "")

    from app.shared.config.app_settings import AppSettings

    settings = AppSettings()
    ai_config = AIConfig.from_settings(settings)

    assert ai_config.copilot_token == "ghp_from_env_test"


def test_copilot_token_falls_back_to_github_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """When AI_COPILOT_TOKEN is empty, fallback to GITHUB_TOKEN env var."""
    monkeypatch.setenv("AI_LLM_PROVIDER", "copilot")
    monkeypatch.delenv("AI_COPILOT_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fallback_github")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.shared.config.app_settings._read_secretkeeper_secret", lambda _key: "")

    from app.shared.config.app_settings import AppSettings

    settings = AppSettings()
    ai_config = AIConfig.from_settings(settings)

    assert ai_config.copilot_token == "ghp_fallback_github"

