from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ai.config import AIConfig
from app.services.ai.interfaces import ChatMessage
from app.services.ai.providers.openai_llm import OpenAILLMProvider


class _FakeAsyncEventStream:
    def __init__(self, events: list[SimpleNamespace]) -> None:
        self._events = events

    def __aiter__(self):
        self._iterator = iter(self._events)
        return self

    async def __anext__(self):
        try:
            return next(self._iterator)
        except StopIteration as stop_iteration:
            raise StopAsyncIteration from stop_iteration


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> OpenAILLMProvider:
    """Create provider with mocked AsyncOpenAI client."""
    mock_responses = MagicMock()
    mock_client = SimpleNamespace(responses=mock_responses)

    mock_async_openai = MagicMock(return_value=mock_client)
    monkeypatch.setattr(
        "app.services.ai.providers.openai_llm.AsyncOpenAI",
        mock_async_openai,
    )

    config = AIConfig(openai_api_key="test-key", openai_llm_model="gpt-5.2")
    return OpenAILLMProvider(config)


@pytest.mark.asyncio
async def test_chat_uses_responses_api_with_json_mapping(
    provider: OpenAILLMProvider,
) -> None:
    usage = SimpleNamespace(input_tokens=10, output_tokens=5, total_tokens=15)
    fake_response = SimpleNamespace(
        output_text='{"ok": true}',
        model="gpt-5.2",
        usage=usage,
    )
    provider.client.responses.create = AsyncMock(return_value=fake_response)

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

    provider.client.responses.create.assert_awaited_once()
    call_kwargs = provider.client.responses.create.await_args.kwargs
    assert call_kwargs["model"] == "gpt-5.2"
    assert call_kwargs["max_output_tokens"] == 120
    assert call_kwargs["text"] == {"format": {"type": "json_object"}}
    assert isinstance(call_kwargs["input"], list)
    assert call_kwargs["input"][0]["role"] == "system"
    assert call_kwargs["input"][1]["content"][0]["text"] == "Return JSON"


@pytest.mark.asyncio
async def test_chat_extracts_text_from_structured_output(
    provider: OpenAILLMProvider,
) -> None:
    content_item = SimpleNamespace(text=SimpleNamespace(value="hello world"))
    output_item = SimpleNamespace(content=[content_item])
    fake_response = SimpleNamespace(
        output_text="",
        output=[output_item],
        model="gpt-5.2",
        usage=None,
    )
    provider.client.responses.create = AsyncMock(return_value=fake_response)

    result = await provider.chat(messages=[ChatMessage(role="user", content="hi")])

    assert result.content == "hello world"


@pytest.mark.asyncio
async def test_stream_yields_single_chunk_from_responses_api(
    provider: OpenAILLMProvider,
) -> None:
    fake_stream = _FakeAsyncEventStream(
        [
            SimpleNamespace(type="response.output_text.delta", delta="streamed "),
            SimpleNamespace(type="response.output_text.delta", delta="answer"),
        ]
    )
    provider.client.responses.create = AsyncMock(return_value=fake_stream)

    chunks = []
    async for chunk in await provider.chat(
        messages=[ChatMessage(role="user", content="stream this")],
        stream=True,
    ):
        chunks.append(chunk)

    assert chunks == ["streamed ", "answer"]
