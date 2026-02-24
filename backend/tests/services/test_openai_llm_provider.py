from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai.config import AIConfig
from app.services.ai.interfaces import ChatMessage
from app.services.ai.providers.openai_llm import OpenAILLMProvider


class _FakeAsyncChunkStream:
    def __init__(self, chunks: list[SimpleNamespace]) -> None:
        self._chunks = chunks

    def __aiter__(self):
        self._iterator = iter(self._chunks)
        return self

    async def __anext__(self):
        try:
            return next(self._iterator)
        except StopIteration as stop_iteration:
            raise StopAsyncIteration from stop_iteration


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> OpenAILLMProvider:
    """Create provider with mocked AsyncOpenAI client (Chat Completions)."""
    mock_completions = MagicMock()
    mock_chat = SimpleNamespace(completions=mock_completions)
    mock_client = SimpleNamespace(chat=mock_chat)

    monkeypatch.setattr(
        "app.services.ai.providers.openai_client._client",
        mock_client,
    )

    config = AIConfig(openai_api_key="test-key", openai_llm_model="gpt-5.2")
    return OpenAILLMProvider(config)


def _make_completion(content: str, model: str = "gpt-5.2", prompt_tokens: int = 10, completion_tokens: int = 5) -> SimpleNamespace:
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice], model=model, usage=usage)


@pytest.mark.asyncio
async def test_chat_uses_chat_completions_with_json_format(
    provider: OpenAILLMProvider,
) -> None:
    fake_response = _make_completion('{"ok": true}')
    provider.client.chat.completions.create = AsyncMock(return_value=fake_response)

    messages = [
        ChatMessage(role="system", content="You are helpful"),
        ChatMessage(role="user", content="Return JSON"),
    ]

    result = await provider.chat(
        messages=messages,
        max_tokens=120,
        response_format={"type": "json_object"},
    )

    assert result.content == '{"ok": true}'
    assert result.model == "gpt-5.2"
    assert result.usage == {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    }

    provider.client.chat.completions.create.assert_awaited_once()
    call_kwargs = provider.client.chat.completions.create.await_args.kwargs
    assert call_kwargs["model"] == "gpt-5.2"
    assert call_kwargs["max_tokens"] == 120
    assert call_kwargs["response_format"] == {"type": "json_object"}
    assert isinstance(call_kwargs["messages"], list)
    assert call_kwargs["messages"][0] == {"role": "system", "content": "You are helpful"}
    assert call_kwargs["messages"][1] == {"role": "user", "content": "Return JSON"}


@pytest.mark.asyncio
async def test_chat_returns_plain_text_content(
    provider: OpenAILLMProvider,
) -> None:
    fake_response = _make_completion("hello world")
    provider.client.chat.completions.create = AsyncMock(return_value=fake_response)

    result = await provider.chat(messages=[ChatMessage(role="user", content="hi")])

    assert result.content == "hello world"


@pytest.mark.asyncio
async def test_stream_yields_delta_chunks(
    provider: OpenAILLMProvider,
) -> None:
    def _make_chunk(delta_content: str | None) -> SimpleNamespace:
        delta = SimpleNamespace(content=delta_content)
        choice = SimpleNamespace(delta=delta)
        return SimpleNamespace(choices=[choice])

    fake_stream = _FakeAsyncChunkStream([
        _make_chunk("streamed "),
        _make_chunk("answer"),
        _make_chunk(None),
    ])
    provider.client.chat.completions.create = AsyncMock(return_value=fake_stream)

    chunks = []
    async for chunk in await provider.chat(
        messages=[ChatMessage(role="user", content="stream this")],
        stream=True,
    ):
        chunks.append(chunk)

    assert chunks == ["streamed ", "answer"]
