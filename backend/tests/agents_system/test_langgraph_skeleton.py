"""
Tests for LangGraph skeleton and graph compilation.

Phase 1: Verify basic graph structure can be created and compiled.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.agents_system.langgraph import graph_factory as graph_factory_module
from app.agents_system.langgraph.graph_factory import build_project_chat_graph
from app.agents_system.langgraph.nodes import context as context_node_module
from app.agents_system.langgraph.nodes.stage_routing import ProjectStage
from app.agents_system.langgraph.state import GraphState


def test_graph_can_be_compiled():
    """Test that the advanced graph can be compiled without errors."""
    mock_db = MagicMock()
    graph = build_project_chat_graph(db=mock_db)
    assert graph is not None


def test_graph_state_model():
    """Test that GraphState type is properly defined."""
    state: GraphState = {
        "project_id": "test-1",
        "user_message": "test message",
        "current_project_state": {},
        "success": False,
    }

    assert state["project_id"] == "test-1"
    assert state["user_message"] == "test message"


@pytest.mark.asyncio
async def test_build_context_summary_uses_routed_stage_for_context_pack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class _FakePack:
        budget_meta = {"used_tokens": 12, "dropped_sections": []}
        sections: list[str] = []

        def to_prompt(self) -> str:
            return "packed summary"

    def fake_build_context_pack(stage, project_state, budget_tokens, thread_summary):
        captured["stage"] = stage
        captured["project_state"] = project_state
        captured["budget_tokens"] = budget_tokens
        captured["thread_summary"] = thread_summary
        return _FakePack()

    monkeypatch.setattr(
        context_node_module,
        "get_app_settings",
        lambda: SimpleNamespace(
            aaa_context_compaction_enabled=True,
            aaa_context_compact_threshold_tokens=256,
        ),
    )
    monkeypatch.setattr(context_node_module, "build_context_pack", fake_build_context_pack)

    result = await context_node_module.build_context_summary_node(
        {
            "project_id": "proj-1",
            "next_stage": ProjectStage.VALIDATE.value,
            "current_project_state": {"requirements": [{"id": "r1"}]},
            "thread_summary": "carry forward",
        },
        db=MagicMock(),
    )

    assert captured["stage"] == ProjectStage.VALIDATE.value
    assert result["context_summary"] == "packed summary"


@pytest.mark.asyncio
async def test_graph_classifies_stage_before_building_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []

    async def fake_load_state(_state, _db):
        call_order.append("load_state")
        return {"current_project_state": {"requirements": [{"id": "r1"}]}}

    def fake_classify_stage(state):
        call_order.append("classify_stage")
        assert state.get("current_project_state") == {"requirements": [{"id": "r1"}]}
        return {"next_stage": ProjectStage.VALIDATE.value}

    async def fake_build_summary(state, _db):
        call_order.append(f"build_summary:{state.get('next_stage')}")
        return {"context_summary": "summary"}

    def fake_build_research(_state):
        call_order.append("build_research")
        return {"research_plan": [], "stage_directives": "", "mindmap_guidance": None}

    async def fake_run_agent(_state):
        call_order.append("run_agent")
        return {"agent_output": "done", "intermediate_steps": [], "success": True}

    async def fake_persist_messages(_state, _db):
        call_order.append("persist_messages")
        return {}

    async def fake_postprocess(_state, _response_message_id):
        call_order.append("postprocess")
        return {}

    async def fake_apply_updates(_state, _db):
        call_order.append("apply_updates")
        return {"updated_project_state": {"requirements": [{"id": "r1"}]}}

    monkeypatch.setattr(graph_factory_module, "load_project_state_node", fake_load_state)
    monkeypatch.setattr(graph_factory_module, "classify_next_stage", fake_classify_stage)
    monkeypatch.setattr(graph_factory_module, "build_context_summary_node", fake_build_summary)
    monkeypatch.setattr(graph_factory_module, "build_research_plan_node", fake_build_research)
    monkeypatch.setattr(graph_factory_module, "run_agent_node", fake_run_agent)
    monkeypatch.setattr(graph_factory_module, "persist_messages_node", fake_persist_messages)
    monkeypatch.setattr(graph_factory_module, "postprocess_node", fake_postprocess)
    monkeypatch.setattr(graph_factory_module, "apply_state_updates_node", fake_apply_updates)
    monkeypatch.setattr(graph_factory_module, "should_route_to_cost_estimator", lambda _state: False)
    monkeypatch.setattr(
        graph_factory_module,
        "get_app_settings",
        lambda: SimpleNamespace(aaa_thread_memory_enabled=False),
    )

    graph = build_project_chat_graph(db=MagicMock(), enable_stage_routing=False)

    await graph.ainvoke(
        {
            "project_id": "proj-1",
            "user_message": "validate this design",
            "success": False,
        }
    )

    assert call_order[:3] == [
        "load_state",
        "classify_stage",
        f"build_summary:{ProjectStage.VALIDATE.value}",
    ]


@pytest.mark.asyncio
async def test_graph_routes_extract_requirements_to_stage_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []

    async def fake_load_state(_state, _db):
        call_order.append("load_state")
        return {
            "current_project_state": {
                "referenceDocuments": [{"id": "doc-1", "parseStatus": "parsed"}],
            }
        }

    def fake_classify_stage(_state):
        call_order.append("classify_stage")
        return {"next_stage": ProjectStage.EXTRACT_REQUIREMENTS.value}

    async def fake_build_summary(state, _db):
        call_order.append(f"build_summary:{state.get('next_stage')}")
        return {"context_summary": "summary"}

    async def fake_extract_requirements(_state, _db):
        call_order.append("extract_requirements")
        return {
            "agent_output": "requirements extracted",
            "final_answer": "requirements extracted",
            "handled_by_stage_worker": True,
            "success": True,
        }

    def fake_build_research(_state):
        raise AssertionError("research path should be skipped for extract_requirements")

    async def fake_run_agent(_state):
        raise AssertionError("generic agent should be skipped for extract_requirements")

    async def fake_persist_messages(_state, _db):
        call_order.append("persist_messages")
        return {}

    async def fake_postprocess(_state, _response_message_id):
        raise AssertionError("postprocess should be skipped for handled stage workers")

    async def fake_apply_updates(_state, _db):
        raise AssertionError("apply_updates should be skipped for handled stage workers")

    monkeypatch.setattr(graph_factory_module, "load_project_state_node", fake_load_state)
    monkeypatch.setattr(graph_factory_module, "classify_next_stage", fake_classify_stage)
    monkeypatch.setattr(graph_factory_module, "build_context_summary_node", fake_build_summary)
    monkeypatch.setattr(
        graph_factory_module,
        "execute_extract_requirements_node",
        fake_extract_requirements,
    )
    monkeypatch.setattr(graph_factory_module, "build_research_plan_node", fake_build_research)
    monkeypatch.setattr(graph_factory_module, "run_agent_node", fake_run_agent)
    monkeypatch.setattr(graph_factory_module, "persist_messages_node", fake_persist_messages)
    monkeypatch.setattr(graph_factory_module, "postprocess_node", fake_postprocess)
    monkeypatch.setattr(graph_factory_module, "apply_state_updates_node", fake_apply_updates)
    monkeypatch.setattr(
        graph_factory_module,
        "get_app_settings",
        lambda: SimpleNamespace(aaa_thread_memory_enabled=False),
    )

    graph = build_project_chat_graph(db=MagicMock(), enable_stage_routing=False)

    result = await graph.ainvoke(
        {
            "project_id": "proj-1",
            "user_message": "continue",
            "success": False,
        }
    )

    assert result["final_answer"] == "requirements extracted"
    assert call_order == [
        "load_state",
        "classify_stage",
        f"build_summary:{ProjectStage.EXTRACT_REQUIREMENTS.value}",
        "extract_requirements",
        "persist_messages",
    ]


@pytest.mark.asyncio
async def test_graph_routes_propose_candidate_through_research_worker_and_architecture_planner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []

    async def fake_load_state(_state, _db):
        call_order.append("load_state")
        return {
            "current_project_state": {
                "requirements": [
                    {"id": "req-1", "title": "99.9% uptime"},
                ],
            }
        }

    def fake_classify_stage(_state):
        call_order.append("classify_stage")
        return {"next_stage": ProjectStage.PROPOSE_CANDIDATE.value}

    async def fake_build_summary(state, _db):
        call_order.append(f"build_summary:{state.get('next_stage')}")
        return {"context_summary": "summary"}

    async def fake_build_research(_state):
        call_order.append("build_research")
        return {
            "research_plan": ["Front Door reliability guidance"],
            "stage_directives": "architecture stage",
            "mindmap_guidance": None,
        }

    async def fake_research_worker(state):
        call_order.append("research_worker")
        assert state.get("research_plan") == ["Front Door reliability guidance"]
        return {
            "research_evidence_packets": [
                {
                    "packet_id": "packet-1",
                    "focus": "Front Door reliability guidance",
                }
            ],
            "research_execution_artifact": {
                "status": "completed",
                "packets_created": 1,
            },
        }

    def fake_build_mindmap_guidance(_state):
        call_order.append("build_mindmap_guidance")
        return {"mindmap_guidance": None}

    def fake_prepare_architecture_handoff(state):
        call_order.append("prepare_architecture_handoff")
        return {
            "agent_handoff_context": {
                "research_evidence_packets": state.get("research_evidence_packets"),
                "research_execution_artifact": state.get("research_execution_artifact"),
            },
            "current_agent": "architecture_planner",
        }

    async def fake_architecture_planner(state):
        call_order.append("architecture_planner")
        handoff = state.get("agent_handoff_context") or {}
        packets = handoff.get("research_evidence_packets") or []
        assert packets[0]["packet_id"] == "packet-1"
        assert handoff.get("research_execution_artifact", {}).get("status") == "completed"
        return {
            "agent_output": "candidate ready",
            "intermediate_steps": [],
            "success": True,
            "error": None,
        }

    async def fake_persist_messages(_state, _db):
        call_order.append("persist_messages")
        return {}

    async def fake_postprocess(state, _response_message_id):
        call_order.append("postprocess")
        return {"final_answer": state.get("agent_output")}

    async def fake_apply_updates(_state, _db):
        call_order.append("apply_updates")
        return {}

    monkeypatch.setattr(graph_factory_module, "load_project_state_node", fake_load_state)
    monkeypatch.setattr(graph_factory_module, "classify_next_stage", fake_classify_stage)
    monkeypatch.setattr(graph_factory_module, "build_context_summary_node", fake_build_summary)
    monkeypatch.setattr(graph_factory_module, "build_research_plan_node", fake_build_research)
    monkeypatch.setattr(graph_factory_module, "execute_research_worker_node", fake_research_worker)
    monkeypatch.setattr(
        graph_factory_module,
        "_pass_through_mindmap_guidance",
        fake_build_mindmap_guidance,
    )
    monkeypatch.setattr(
        graph_factory_module,
        "prepare_architecture_planner_handoff",
        fake_prepare_architecture_handoff,
    )
    monkeypatch.setattr(
        graph_factory_module,
        "architecture_planner_node",
        fake_architecture_planner,
    )
    monkeypatch.setattr(graph_factory_module, "persist_messages_node", fake_persist_messages)
    monkeypatch.setattr(graph_factory_module, "postprocess_node", fake_postprocess)
    monkeypatch.setattr(graph_factory_module, "apply_state_updates_node", fake_apply_updates)
    monkeypatch.setattr(graph_factory_module, "should_route_to_cost_estimator", lambda _state: False)
    monkeypatch.setattr(
        graph_factory_module,
        "get_app_settings",
        lambda: SimpleNamespace(aaa_thread_memory_enabled=False),
    )

    graph = build_project_chat_graph(db=MagicMock(), enable_stage_routing=False)

    result = await graph.ainvoke(
        {
            "project_id": "proj-1",
            "user_message": "design the target architecture",
            "success": False,
        }
    )

    assert result["final_answer"] == "candidate ready"
    assert call_order == [
        "load_state",
        "classify_stage",
        f"build_summary:{ProjectStage.PROPOSE_CANDIDATE.value}",
        "build_research",
        "research_worker",
        "build_mindmap_guidance",
        "prepare_architecture_handoff",
        "architecture_planner",
        "persist_messages",
        "postprocess",
        "apply_updates",
    ]

