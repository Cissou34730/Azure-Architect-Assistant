from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from app.agents_system.langgraph.nodes import agent_native


class _FakeBoundLLM:
    async def ainvoke(self, _messages):
        return AIMessage(content="bound response")


class _FakeBaseLLM:
    def __init__(self) -> None:
        self.bound_tools = None

    def bind_tools(self, tools):
        self.bound_tools = tools
        return _FakeBoundLLM()


class _FakeGraph:
    def __init__(self) -> None:
        self.initial_state = None

    async def ainvoke(self, initial_state):
        self.initial_state = initial_state
        return {"messages": []}


@pytest.mark.asyncio
async def test_run_stage_aware_agent_uses_ai_service_chat_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_build_tools(_mcp_client, project_id: str = "", **kwargs) -> list[object]:
        captured["project_id"] = project_id
        return []

    def _fake_compile(llm, tools, final_llm):
        captured["llm"] = llm
        captured["tools"] = tools
        captured["final_llm"] = final_llm
        return _FakeGraph()

    class _FakeAIService:
        def create_chat_llm(self, *, temperature: float):
            captured["temperature"] = temperature
            model = _FakeBaseLLM()
            captured["base_llm"] = model
            return model

    monkeypatch.setattr(agent_native, "_build_tools", _fake_build_tools)
    monkeypatch.setattr(agent_native, "_compile_agent_graph", _fake_compile)
    monkeypatch.setattr(agent_native, "get_ai_service", lambda: _FakeAIService())
    monkeypatch.setattr(
        agent_native,
        "get_app_settings",
        lambda: SimpleNamespace(chat_temperature=0.35),
    )

    result = await agent_native.run_stage_aware_agent(
        {"user_message": "hello", "project_id": "proj-1"},
        mcp_client=object(),
    )

    assert captured["temperature"] == 0.35
    assert captured["project_id"] == "proj-1"
    assert isinstance(captured["base_llm"], _FakeBaseLLM)
    assert isinstance(captured["llm"], _FakeBoundLLM)
    assert captured["final_llm"] is captured["base_llm"]
    assert result["success"] is True
    assert result["agent_output"] == ""


@pytest.mark.asyncio
async def test_run_stage_aware_agent_uses_bound_llm_for_copilot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_build_tools(_mcp_client, project_id: str = "", **kwargs) -> list[object]:
        captured["project_id"] = project_id
        return []

    def _fake_compile(llm, tools, final_llm):
        captured["llm"] = llm
        captured["tools"] = tools
        captured["final_llm"] = final_llm
        return _FakeGraph()

    class _FakeAIService:
        def create_chat_llm(self, *, temperature: float):
            captured["temperature"] = temperature
            model = _FakeBaseLLM()
            captured["base_llm"] = model
            return model

    monkeypatch.setattr(agent_native, "_build_tools", _fake_build_tools)
    monkeypatch.setattr(agent_native, "_compile_agent_graph", _fake_compile)
    monkeypatch.setattr(agent_native, "get_ai_service", lambda: _FakeAIService())
    monkeypatch.setattr(
        agent_native,
        "get_app_settings",
        lambda: SimpleNamespace(chat_temperature=0.2),
    )

    result = await agent_native.run_stage_aware_agent(
        {"user_message": "hello", "project_id": "proj-2"},
        mcp_client=object(),
    )

    assert captured["project_id"] == "proj-2"
    assert captured["temperature"] == 0.2
    assert isinstance(captured["base_llm"], _FakeBaseLLM)
    assert isinstance(captured["llm"], _FakeBoundLLM)
    assert captured["final_llm"] is captured["base_llm"]
    assert result["success"] is True


@pytest.mark.asyncio
async def test_run_stage_aware_agent_emits_stream_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, dict[str, object]]] = []

    async def _fake_build_tools(_mcp_client, project_id: str = "", **kwargs) -> list[object]:
        assert project_id == "proj-stream"
        return []

    async def _fake_streaming_loop(*, event_callback, **_kwargs):
        await event_callback("message_start", {"role": "assistant"})
        await event_callback("token", {"text": "hello"})
        return {
            "agent_output": "hello",
            "intermediate_steps": [],
            "success": True,
            "error": None,
        }

    class _FakeAIService:
        def create_chat_llm(self, *, temperature: float):
            assert temperature == 0.5
            return _FakeBaseLLM()

    monkeypatch.setattr(agent_native, "_build_tools", _fake_build_tools)
    monkeypatch.setattr(agent_native, "_run_streaming_agent_loop", _fake_streaming_loop)
    monkeypatch.setattr(agent_native, "get_ai_service", lambda: _FakeAIService())
    monkeypatch.setattr(
        agent_native,
        "get_app_settings",
        lambda: SimpleNamespace(chat_temperature=0.5),
    )

    async def _callback(event_type: str, payload: dict[str, object]) -> None:
        events.append((event_type, payload))

    result = await agent_native.run_stage_aware_agent(
        {
            "user_message": "hello",
            "project_id": "proj-stream",
            "event_callback": _callback,
        },
        mcp_client=object(),
    )

    assert result["agent_output"] == "hello"
    assert events == [
        ("message_start", {"role": "assistant"}),
        ("token", {"text": "hello"}),
    ]
