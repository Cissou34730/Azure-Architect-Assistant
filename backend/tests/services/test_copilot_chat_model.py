"""Tests for the CopilotChatModel – a LangChain BaseChatModel backed by the Copilot SDK."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.shared.ai.providers.copilot_chat_model import (
    CopilotChatModel,
    _format_messages_to_prompt,
    _parse_tool_calls,
)

# ── Helpers ────────────────────────────────────────────────────────────


class _FakeRuntime:
    """Fake CopilotRuntime for testing."""

    def __init__(self, reply: str = "Hello!") -> None:
        self.reply = reply
        self.last_prompt: str | None = None
        self.last_model: str | None = None
        self.last_system_message: str | None = None

    async def send_message(
        self, *, prompt: str, model: str, system_message: str | None, timeout: float
    ) -> str:
        self.last_prompt = prompt
        self.last_model = model
        self.last_system_message = system_message
        return self.reply

    async def stream_message(
        self, *, prompt: str, model: str, system_message: str | None, timeout: float
    ) -> AsyncIterator[str]:
        self.last_prompt = prompt
        self.last_model = model
        self.last_system_message = system_message
        for word in self.reply.split(" "):
            yield word + " "


# ── Message formatting ────────────────────────────────────────────────


def test_format_messages_system_and_human() -> None:
    messages = [
        SystemMessage(content="You are helpful"),
        HumanMessage(content="hello"),
    ]
    system, prompt = _format_messages_to_prompt(messages)
    assert system == "You are helpful"
    assert "hello" in prompt


def test_format_messages_tool_results_included() -> None:
    messages = [
        HumanMessage(content="Search for cats"),
        AIMessage(content="", tool_calls=[{"id": "c1", "name": "search", "args": {"q": "cats"}}]),
        ToolMessage(content="Found 3 cats", tool_call_id="c1"),
        HumanMessage(content="Tell me more"),
    ]
    _system, prompt = _format_messages_to_prompt(messages)
    assert "Found 3 cats" in prompt
    assert "Tell me more" in prompt


def test_format_messages_multiple_system_merged() -> None:
    messages = [
        SystemMessage(content="Be concise"),
        SystemMessage(content="Use markdown"),
        HumanMessage(content="hi"),
    ]
    system, _prompt = _format_messages_to_prompt(messages)
    assert "Be concise" in system
    assert "Use markdown" in system


# ── Tool call parsing ─────────────────────────────────────────────────


def test_parse_tool_calls_single() -> None:
    text = (
        'I need to search.\n'
        '<tool_call>\n'
        '{"name": "search", "arguments": {"query": "cats"}}\n'
        '</tool_call>'
    )
    calls = _parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "search"
    assert calls[0]["args"] == {"query": "cats"}
    assert "id" in calls[0]


def test_parse_tool_calls_multiple() -> None:
    text = (
        '<tool_call>\n'
        '{"name": "search", "arguments": {"query": "cats"}}\n'
        '</tool_call>\n'
        '<tool_call>\n'
        '{"name": "get_doc", "arguments": {"id": "42"}}\n'
        '</tool_call>'
    )
    calls = _parse_tool_calls(text)
    assert len(calls) == 2
    assert calls[0]["name"] == "search"
    assert calls[1]["name"] == "get_doc"


def test_parse_tool_calls_none_when_no_tags() -> None:
    text = "Just a regular response with no tool calls."
    assert _parse_tool_calls(text) is None


def test_parse_tool_calls_none_on_invalid_json() -> None:
    text = "<tool_call>\nnot valid json\n</tool_call>"
    assert _parse_tool_calls(text) is None


# ── BaseChatModel interface ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_basic_chat_returns_ai_message(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRuntime("Hello from Claude!")
    monkeypatch.setattr(
        "app.shared.ai.providers.copilot_chat_model.get_copilot_runtime",
        AsyncMock(return_value=fake),
    )

    model = CopilotChatModel(model_name="claude-sonnet-4.6", timeout=30.0)
    result = await model.ainvoke([HumanMessage(content="hi")])

    assert isinstance(result, AIMessage)
    assert result.content == "Hello from Claude!"
    assert fake.last_model == "claude-sonnet-4.6"


@pytest.mark.asyncio
async def test_chat_with_tools_returns_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    tool_response = (
        'Let me search for that.\n'
        '<tool_call>\n'
        '{"name": "search", "arguments": {"query": "azure architecture"}}\n'
        '</tool_call>'
    )
    fake = _FakeRuntime(tool_response)
    monkeypatch.setattr(
        "app.shared.ai.providers.copilot_chat_model.get_copilot_runtime",
        AsyncMock(return_value=fake),
    )

    model = CopilotChatModel(model_name="claude-sonnet-4.6", timeout=30.0)
    tools = [
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
    bound = model.bind_tools(tools)
    result = await bound.ainvoke([HumanMessage(content="find azure patterns")])

    assert isinstance(result, AIMessage)
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "search"
    assert result.tool_calls[0]["args"] == {"query": "azure architecture"}


@pytest.mark.asyncio
async def test_tools_bound_but_no_call_in_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """When tools are bound but the model decides not to use them."""
    fake = _FakeRuntime("I already know the answer: 42.")
    monkeypatch.setattr(
        "app.shared.ai.providers.copilot_chat_model.get_copilot_runtime",
        AsyncMock(return_value=fake),
    )

    model = CopilotChatModel(model_name="gpt-5.2", timeout=30.0)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "Search",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]
    bound = model.bind_tools(tools)
    result = await bound.ainvoke([HumanMessage(content="what is 6*7?")])

    assert isinstance(result, AIMessage)
    assert result.content == "I already know the answer: 42."
    assert not result.tool_calls


@pytest.mark.asyncio
async def test_tool_schemas_injected_into_system_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify tool definitions appear in the system message sent to the SDK."""
    fake = _FakeRuntime("No tools needed.")
    monkeypatch.setattr(
        "app.shared.ai.providers.copilot_chat_model.get_copilot_runtime",
        AsyncMock(return_value=fake),
    )

    model = CopilotChatModel(model_name="claude-sonnet-4.6", timeout=30.0)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "lookup",
                "description": "Look up a record",
                "parameters": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                },
            },
        }
    ]
    bound = model.bind_tools(tools)
    await bound.ainvoke([
        SystemMessage(content="Be helpful"),
        HumanMessage(content="find record 5"),
    ])

    # The system message should contain the tool schema
    assert fake.last_system_message is not None
    assert "lookup" in fake.last_system_message
    assert "Look up a record" in fake.last_system_message
    # Original system message preserved
    assert "Be helpful" in fake.last_system_message


def test_llm_type() -> None:
    model = CopilotChatModel(model_name="claude-sonnet-4.6", timeout=30.0)
    assert model._llm_type == "copilot-sdk"


@pytest.mark.asyncio
async def test_streaming_yields_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRuntime("Hello from streaming!")
    monkeypatch.setattr(
        "app.shared.ai.providers.copilot_chat_model.get_copilot_runtime",
        AsyncMock(return_value=fake),
    )

    model = CopilotChatModel(model_name="claude-sonnet-4.6", timeout=30.0)
    chunks: list[str] = []
    async for chunk in model.astream([HumanMessage(content="hi")]):
        chunks.append(chunk.content)

    joined = "".join(chunks)
    assert "Hello" in joined
    assert "streaming" in joined


@pytest.mark.asyncio
async def test_streaming_injects_tools_into_system_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify tool definitions appear in the system message during streaming."""
    fake = _FakeRuntime("No tools needed in stream.")
    monkeypatch.setattr(
        "app.shared.ai.providers.copilot_chat_model.get_copilot_runtime",
        AsyncMock(return_value=fake),
    )

    model = CopilotChatModel(model_name="gpt-5.2", timeout=30.0)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "Search for info",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]
    bound = model.bind(tools=tools)
    chunks: list[str] = []
    async for chunk in bound.astream([
        SystemMessage(content="Be concise"),
        HumanMessage(content="hello"),
    ]):
        chunks.append(chunk.content)

    assert fake.last_system_message is not None
    assert "search" in fake.last_system_message
    assert "Search for info" in fake.last_system_message
    assert "Be concise" in fake.last_system_message


@pytest.mark.asyncio
async def test_streaming_parses_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify <tool_call> blocks are detected and returned during streaming."""
    tool_response = (
        'Let me search.\n'
        '<tool_call>\n'
        '{"name": "search", "arguments": {"q": "azure"}}\n'
        '</tool_call>'
    )
    fake = _FakeRuntime(tool_response)
    monkeypatch.setattr(
        "app.shared.ai.providers.copilot_chat_model.get_copilot_runtime",
        AsyncMock(return_value=fake),
    )

    model = CopilotChatModel(model_name="gpt-5.2", timeout=30.0)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "Search",
                "parameters": {"type": "object", "properties": {"q": {"type": "string"}}},
            },
        }
    ]
    bound = model.bind(tools=tools)
    chunks = []
    async for chunk in bound.astream([HumanMessage(content="find azure info")]):
        chunks.append(chunk)

    assert len(chunks) == 1
    # astream yields AIMessageChunk objects directly
    msg = chunks[0]
    assert hasattr(msg, "tool_calls")
    assert msg.tool_calls[0]["name"] == "search"
    assert msg.tool_calls[0]["args"] == {"q": "azure"}

