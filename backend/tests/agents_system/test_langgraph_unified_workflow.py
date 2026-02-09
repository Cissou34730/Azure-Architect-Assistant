from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents_system.langgraph import adapter as adapter_module
from app.agents_system.langgraph.nodes import agent as agent_node
from app.agents_system.services.state_update_parser import extract_state_updates


@pytest.mark.asyncio
async def test_execute_project_chat_uses_unified_advanced_graph(monkeypatch):
    captured: dict[str, object] = {}

    class DummyGraph:
        async def ainvoke(self, initial_state):
            captured["initial_state"] = initial_state
            return {
                "final_answer": "ok",
                "success": True,
                "intermediate_steps": [],
            }

    def fake_build_advanced(
        db,
        response_message_id: str,
        enable_stage_routing: bool,
        enable_multi_agent: bool,
    ):
        captured["db"] = db
        captured["response_message_id"] = response_message_id
        captured["enable_stage_routing"] = enable_stage_routing
        captured["enable_multi_agent"] = enable_multi_agent
        return DummyGraph()

    monkeypatch.setattr(
        adapter_module, "build_advanced_project_chat_graph", fake_build_advanced
    )

    result = await adapter_module.execute_project_chat(
        project_id="proj-1",
        user_message="hello",
        db=object(),
    )

    assert captured["enable_stage_routing"] is True
    assert captured["enable_multi_agent"] is False
    assert isinstance(captured.get("response_message_id"), str)
    assert captured["initial_state"]["project_id"] == "proj-1"
    assert captured["initial_state"]["user_message"] == "hello"
    assert result["success"] is True
    assert result["answer"] == "ok"


@pytest.mark.asyncio
async def test_run_agent_node_does_not_fallback_to_legacy_runner(monkeypatch):
    runner = SimpleNamespace(
        mcp_client=object(),
        openai_settings=object(),
        execute_query=AsyncMock(return_value={"output": "legacy"}),
    )

    async def fake_get_runner():
        return runner

    async def fake_run_stage_aware_agent(*args, **kwargs):
        raise ValueError("native failed")

    monkeypatch.setattr(agent_node, "get_agent_runner", fake_get_runner)
    monkeypatch.setattr(agent_node, "run_stage_aware_agent", fake_run_stage_aware_agent)

    result = await agent_node.run_agent_node({"user_message": "hello"})

    assert result["success"] is False
    assert "LangGraph native agent execution failed" in (result.get("error") or "")
    assert runner.execute_query.await_count == 0


@pytest.mark.asyncio
async def test_run_agent_node_bulk_waf_reliability_override_shortcut(monkeypatch):
    get_runner = AsyncMock(
        side_effect=AssertionError("Runner should not be called for direct checklist bulk updates")
    )
    monkeypatch.setattr(agent_node, "get_agent_runner", get_runner)

    state = {
        "user_message": "update the waf reliability checklist to all done",
        "current_project_state": {
            "wafChecklist": {
                "items": [
                    {"id": "re-01", "pillar": "Reliability", "topic": "Availability targets"},
                    {"id": "re-02", "pillar": "Reliability", "topic": "DR plan"},
                    {"id": "se-01", "pillar": "Security", "topic": "Identity"},
                ]
            }
        },
    }

    result = await agent_node.run_agent_node(state)
    assert result["success"] is True
    assert "Risk warning" in (result.get("agent_output") or "")
    assert "AAA_STATE_UPDATE" in (result.get("agent_output") or "")

    updates = extract_state_updates(result["agent_output"], state["user_message"], {})
    assert updates is not None
    waf_items = updates["wafChecklist"]["items"]
    assert len(waf_items) == 2
    assert all(item["pillar"] == "Reliability" for item in waf_items)
    assert all(item["evaluations"][0]["status"] == "covered" for item in waf_items)


@pytest.mark.asyncio
async def test_run_agent_node_bulk_waf_reliability_typo_still_matches(monkeypatch):
    monkeypatch.setattr(
        agent_node,
        "get_agent_runner",
        AsyncMock(side_effect=AssertionError("Runner should not be called")),
    )

    state = {
        "user_message": "update waf reliabilty checklist to all done",
        "current_project_state": {
            "wafChecklist": {
                "items": [{"id": "re-01", "pillar": "Reliability", "topic": "Availability targets"}]
            }
        },
    }

    result = await agent_node.run_agent_node(state)
    assert result["success"] is True
    updates = extract_state_updates(result["agent_output"], state["user_message"], {})
    assert updates is not None
    assert updates["wafChecklist"]["items"][0]["pillar"] == "Reliability"


@pytest.mark.asyncio
async def test_run_agent_node_bulk_waf_without_explicit_waf_word_still_matches(monkeypatch):
    monkeypatch.setattr(
        agent_node,
        "get_agent_runner",
        AsyncMock(side_effect=AssertionError("Runner should not be called")),
    )

    state = {
        "user_message": "reliability checklist all done",
        "current_project_state": {
            "wafChecklist": {
                "items": [
                    {"id": "re-01", "pillar": "Reliability", "topic": "Availability targets"},
                    {"id": "re-02", "pillar": "Reliability", "topic": "DR"},
                ]
            }
        },
    }

    result = await agent_node.run_agent_node(state)
    assert result["success"] is True
    updates = extract_state_updates(result["agent_output"], state["user_message"], {})
    assert updates is not None
    assert len(updates["wafChecklist"]["items"]) == 2


@pytest.mark.asyncio
async def test_run_agent_node_bulk_override_falls_back_when_no_matching_items(monkeypatch):
    runner = SimpleNamespace(
        mcp_client=object(),
        openai_settings=object(),
    )
    monkeypatch.setattr(agent_node, "get_agent_runner", AsyncMock(return_value=runner))
    monkeypatch.setattr(
        agent_node,
        "run_stage_aware_agent",
        AsyncMock(
            return_value={
                "agent_output": "fallback path",
                "intermediate_steps": [],
                "success": True,
                "error": None,
            }
        ),
    )

    state = {
        "user_message": "update the waf reliability checklist to all done",
        "current_project_state": {"wafChecklist": {"items": [{"id": "se-01", "pillar": "Security"}]}},
    }

    result = await agent_node.run_agent_node(state)
    assert result["success"] is True
    assert result["agent_output"] == "fallback path"
