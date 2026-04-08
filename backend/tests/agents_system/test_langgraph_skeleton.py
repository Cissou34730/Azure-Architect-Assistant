"""
Tests for LangGraph skeleton and graph compilation.

Phase 1: Verify basic graph structure can be created and compiled.
"""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.agents_system.langgraph import graph_factory as graph_factory_module
from app.agents_system.langgraph.graph_factory import build_project_chat_graph
from app.agents_system.langgraph.nodes import context as context_node_module
from app.agents_system.langgraph.nodes.stage_routing import ProjectStage
from app.agents_system.langgraph.nodes.validate import execute_validate_stage_worker_node
from app.agents_system.langgraph.state import GraphState
from app.agents_system.services.waf_findings_worker import WAFFindingsWorker
from app.shared.config.settings.agents import AgentsSettingsMixin


def test_graph_can_be_compiled():
    """Test that the advanced graph can be compiled without errors."""
    mock_db = MagicMock()
    graph = build_project_chat_graph(db=mock_db)
    assert graph is not None


def test_phase11_runtime_flags_default_to_enabled() -> None:
    class _Settings(AgentsSettingsMixin):
        pass

    settings = _Settings()

    assert settings.aaa_context_compaction_enabled is True
    assert settings.aaa_thread_memory_enabled is True


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
            aaa_context_max_budget_tokens=1024,
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
    assert captured["budget_tokens"] == 1024
    assert result["context_summary"] == "packed summary"


def test_graph_uses_checkpointer_when_thread_memory_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_compile(self, *, checkpointer=None):  # type: ignore[no-untyped-def]
        captured["checkpointer"] = checkpointer
        return "compiled-graph"

    monkeypatch.setattr(
        graph_factory_module,
        "get_app_settings",
        lambda: SimpleNamespace(aaa_thread_memory_enabled=True),
    )
    monkeypatch.setattr(graph_factory_module, "MemorySaver", lambda: "memory-saver")
    monkeypatch.setattr(graph_factory_module.StateGraph, "compile", fake_compile)

    graph = build_project_chat_graph(db=MagicMock())

    assert graph == "compiled-graph"
    assert captured["checkpointer"] == "memory-saver"


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

    graph = build_project_chat_graph(db=MagicMock())

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

    graph = build_project_chat_graph(db=MagicMock())

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

    graph = build_project_chat_graph(db=MagicMock())

    result = await graph.ainvoke(
        {
            "project_id": "proj-1",
            "user_message": "design the target architecture",
            "success": False,
        }
    )

    assert str(result["final_answer"]).startswith("candidate ready")
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


@pytest.mark.asyncio
async def test_graph_routes_pricing_stage_through_dedicated_cost_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []

    async def fake_load_state(_state, _db):
        call_order.append("load_state")
        return {
            "current_project_state": {
                "candidateArchitectures": [
                    {"id": "candidate-1", "summary": "SWA + Azure Functions + Table Storage"}
                ]
            }
        }

    def fake_classify_stage(_state):
        call_order.append("classify_stage")
        return {"next_stage": ProjectStage.PRICING.value}

    async def fake_build_summary(state, _db):
        call_order.append(f"build_summary:{state.get('next_stage')}")
        return {"context_summary": "summary"}

    async def fake_build_research(_state):
        call_order.append("build_research")
        return {
            "research_plan": ["Azure Pricing meters for Static Web Apps and Functions"],
            "stage_directives": "pricing stage",
            "mindmap_guidance": None,
        }

    async def fake_research_worker(_state):
        raise AssertionError("research worker should be skipped for pricing stage")

    def fake_build_mindmap_guidance(_state):
        call_order.append("build_mindmap_guidance")
        return {"mindmap_guidance": None}

    async def fake_cost_stage_worker(state):
        call_order.append("cost_stage_worker")
        assert state.get("next_stage") == ProjectStage.PRICING.value
        return {
            "agent_output": (
                "Recorded cost estimate at 2026-04-08T12:00:00+00:00 (pricingLines=1).\n\n"
                "AAA_STATE_UPDATE\n"
                "```json\n"
                '{\n  "costEstimates": [{"id": "cost-1", "totalMonthlyCost": 42.0}]}\n'
                "```"
            ),
            "intermediate_steps": [],
            "success": True,
            "error": None,
            "current_agent": "cost_estimator",
        }

    async def fake_run_agent(_state):
        raise AssertionError("generic agent should be skipped for pricing stage")

    async def fake_persist_messages(_state, _db):
        call_order.append("persist_messages")
        return {}

    async def fake_postprocess(_state, _response_message_id):
        call_order.append("postprocess")
        return {
            "combined_updates": {
                "costEstimates": [{"id": "cost-1", "totalMonthlyCost": 42.0}],
            },
            "final_answer": "cost recorded",
        }

    async def fake_apply_updates(_state, _db):
        call_order.append("apply_updates")
        return {
            "updated_project_state": {
                "costEstimates": [{"id": "cost-1", "totalMonthlyCost": 42.0}],
            },
            "final_answer": "cost recorded",
            "success": True,
        }

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
        "execute_cost_stage_worker_node",
        fake_cost_stage_worker,
    )
    monkeypatch.setattr(graph_factory_module, "run_agent_node", fake_run_agent)
    monkeypatch.setattr(graph_factory_module, "persist_messages_node", fake_persist_messages)
    monkeypatch.setattr(graph_factory_module, "postprocess_node", fake_postprocess)
    monkeypatch.setattr(graph_factory_module, "apply_state_updates_node", fake_apply_updates)
    monkeypatch.setattr(graph_factory_module, "should_route_to_cost_estimator", lambda _state: True)
    monkeypatch.setattr(
        graph_factory_module,
        "get_app_settings",
        lambda: SimpleNamespace(aaa_thread_memory_enabled=False),
    )

    graph = build_project_chat_graph(db=MagicMock())

    result = await graph.ainvoke(
        {
            "project_id": "proj-1",
            "user_message": "How much would this run each month?",
            "success": False,
        }
    )

    assert result["final_answer"] == "cost recorded"
    assert call_order == [
        "load_state",
        "classify_stage",
        f"build_summary:{ProjectStage.PRICING.value}",
        "build_research",
        "build_mindmap_guidance",
        "cost_stage_worker",
        "persist_messages",
        "postprocess",
        "apply_updates",
    ]


@pytest.mark.asyncio
async def test_graph_routes_iac_stage_through_dedicated_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []

    async def fake_load_state(_state, _db):
        call_order.append("load_state")
        return {
            "current_project_state": {
                "candidateArchitectures": [
                    {"id": "candidate-1", "summary": "Storage account + App Service"}
                ]
            }
        }

    def fake_classify_stage(_state):
        call_order.append("classify_stage")
        return {"next_stage": ProjectStage.IAC.value}

    async def fake_build_summary(state, _db):
        call_order.append(f"build_summary:{state.get('next_stage')}")
        return {"context_summary": "summary"}

    async def fake_build_research(_state):
        call_order.append("build_research")
        return {
            "research_plan": ["Bicep schema guidance for Storage Accounts"],
            "stage_directives": "iac stage",
            "mindmap_guidance": None,
        }

    async def fake_research_worker(_state):
        raise AssertionError("research worker should be skipped for iac stage")

    def fake_build_mindmap_guidance(_state):
        call_order.append("build_mindmap_guidance")
        return {"mindmap_guidance": None}

    async def fake_iac_stage_worker(state):
        call_order.append("iac_stage_worker")
        assert state.get("next_stage") == ProjectStage.IAC.value
        return {
            "agent_output": (
                "Recorded IaC artifacts at 2026-04-08T12:00:00+00:00 (iacFiles=1).\n\n"
                "AAA_STATE_UPDATE\n"
                "```json\n"
                '{\n  "iacArtifacts": [{"id": "iac-1"}]}\n'
                "```"
            ),
            "intermediate_steps": [],
            "success": True,
            "error": None,
            "current_agent": "iac_generator",
        }

    async def fake_run_agent(_state):
        raise AssertionError("generic agent should be skipped for iac stage")

    async def fake_persist_messages(_state, _db):
        call_order.append("persist_messages")
        return {}

    async def fake_postprocess(_state, _response_message_id):
        call_order.append("postprocess")
        return {
            "combined_updates": {
                "iacArtifacts": [{"id": "iac-1"}],
            },
            "final_answer": "iac recorded",
        }

    async def fake_apply_updates(_state, _db):
        call_order.append("apply_updates")
        return {
            "updated_project_state": {
                "iacArtifacts": [{"id": "iac-1"}],
            },
            "final_answer": "iac recorded",
            "success": True,
        }

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
        "execute_iac_stage_worker_node",
        fake_iac_stage_worker,
    )
    monkeypatch.setattr(graph_factory_module, "run_agent_node", fake_run_agent)
    monkeypatch.setattr(graph_factory_module, "persist_messages_node", fake_persist_messages)
    monkeypatch.setattr(graph_factory_module, "postprocess_node", fake_postprocess)
    monkeypatch.setattr(graph_factory_module, "apply_state_updates_node", fake_apply_updates)
    monkeypatch.setattr(graph_factory_module, "should_route_to_cost_estimator", lambda _state: False)
    monkeypatch.setattr(graph_factory_module, "should_route_to_iac_generator", lambda _state: False)
    monkeypatch.setattr(
        graph_factory_module,
        "get_app_settings",
        lambda: SimpleNamespace(aaa_thread_memory_enabled=False),
    )

    graph = build_project_chat_graph(db=MagicMock())

    result = await graph.ainvoke(
        {
            "project_id": "proj-1",
            "user_message": "Generate Bicep for this architecture",
            "success": False,
        }
    )

    assert result["final_answer"] == "iac recorded"
    assert call_order == [
        "load_state",
        "classify_stage",
        f"build_summary:{ProjectStage.IAC.value}",
        "build_research",
        "build_mindmap_guidance",
        "iac_stage_worker",
        "persist_messages",
        "postprocess",
        "apply_updates",
    ]


@pytest.mark.asyncio
async def test_graph_routes_export_to_dedicated_stage_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []

    async def fake_load_state(_state, _db):
        call_order.append("load_state")
        return {
            "current_project_state": {
                "requirements": [{"id": "req-1"}],
                "traceabilityLinks": [{"id": "link-1"}],
            }
        }

    def fake_classify_stage(_state):
        call_order.append("classify_stage")
        return {"next_stage": ProjectStage.EXPORT.value}

    async def fake_build_summary(state, _db):
        call_order.append(f"build_summary:{state.get('next_stage')}")
        return {"context_summary": "summary"}

    async def fake_export_stage_worker(state):
        call_order.append("export_stage_worker")
        assert state.get("current_project_state", {}).get("requirements") == [{"id": "req-1"}]
        return {
            "agent_output": "AAA_EXPORT\n```json\n{\"ok\":true}\n```",
            "final_answer": "AAA_EXPORT\n```json\n{\"ok\":true}\n```",
            "intermediate_steps": [],
            "handled_by_stage_worker": True,
            "success": True,
        }

    async def fake_build_research(_state):
        raise AssertionError("research path should be skipped for export")

    async def fake_run_agent(_state):
        raise AssertionError("generic agent should be skipped for export")

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
    monkeypatch.setattr(graph_factory_module, "execute_export_stage_worker_node", fake_export_stage_worker)
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

    graph = build_project_chat_graph(db=MagicMock())

    result = await graph.ainvoke(
        {
            "project_id": "proj-1",
            "user_message": "export the deliverable package",
            "success": False,
        }
    )

    assert result["final_answer"] == "AAA_EXPORT\n```json\n{\"ok\":true}\n```"
    assert call_order == [
        "load_state",
        "classify_stage",
        f"build_summary:{ProjectStage.EXPORT.value}",
        "export_stage_worker",
        "persist_messages",
    ]


@pytest.mark.asyncio
async def test_graph_routes_validate_stage_through_validate_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []

    async def fake_load_state(_state, _db):
        call_order.append("load_state")
        return {
            "current_project_state": {
                "candidateArchitectures": [
                    {"id": "candidate-1", "notes": "Public ingress goes straight to App Service."}
                ],
                "referenceDocuments": [
                    {
                        "id": "doc-1",
                        "title": "Azure WAF guidance",
                        "url": "https://learn.microsoft.com/azure/well-architected/security/",
                    }
                ],
                "wafChecklist": {
                    "items": [
                        {
                            "id": "sec-waf-1",
                            "pillar": "Security",
                            "topic": "Protect public entry points with a web application firewall",
                        }
                    ]
                },
            }
        }

    def fake_classify_stage(_state):
        call_order.append("classify_stage")
        return {"next_stage": ProjectStage.VALIDATE.value}

    async def fake_build_summary(state, _db):
        call_order.append(f"build_summary:{state.get('next_stage')}")
        return {"context_summary": "summary"}

    async def fake_build_research(_state):
        call_order.append("build_research")
        return {
            "research_plan": ["Azure WAF checklist for security controls"],
            "stage_directives": "validation stage",
            "mindmap_guidance": None,
        }

    async def fake_research_worker(_state):
        raise AssertionError("research worker should be skipped for validate stage")

    def fake_build_mindmap_guidance(_state):
        call_order.append("build_mindmap_guidance")
        return {"mindmap_guidance": None}

    async def fake_validate_stage_worker(state):
        call_order.append("validate_stage_worker")
        assert state.get("next_stage") == ProjectStage.VALIDATE.value
        return {
            "agent_output": (
                "Recorded validation results at 2026-04-08T12:00:00+00:00 (findings=1, wafEvaluations=1).\n\n"
                "AAA_STATE_UPDATE\n"
                "```json\n"
                "{\n"
                '  "findings": [{"id": "finding-sec-waf-1"}],\n'
                '  "wafChecklist": {"items": [{"id": "sec-waf-1"}]}\n'
                "}\n"
                "```"
            ),
            "intermediate_steps": [],
            "success": True,
            "error": None,
        }

    async def fake_run_agent(_state):
        raise AssertionError("generic agent should be skipped for validate stage")

    async def fake_persist_messages(_state, _db):
        call_order.append("persist_messages")
        return {}

    async def fake_postprocess(_state, _response_message_id):
        call_order.append("postprocess")
        return {
            "combined_updates": {
                "findings": [{"id": "finding-sec-waf-1"}],
                "wafChecklist": {"items": [{"id": "sec-waf-1"}]},
            },
            "final_answer": "validation recorded",
        }

    async def fake_apply_updates(_state, _db):
        call_order.append("apply_updates")
        return {
            "updated_project_state": {
                "findings": [{"id": "finding-sec-waf-1"}],
                "wafChecklist": {"items": [{"id": "sec-waf-1"}]},
            },
            "final_answer": "validation recorded",
            "success": True,
        }

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
        "execute_validate_stage_worker_node",
        fake_validate_stage_worker,
    )
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

    graph = build_project_chat_graph(db=MagicMock())

    result = await graph.ainvoke(
        {
            "project_id": "proj-1",
            "user_message": "validate this design against WAF",
            "success": False,
        }
    )

    assert result["final_answer"] == "validation recorded"
    assert call_order == [
        "load_state",
        "classify_stage",
        f"build_summary:{ProjectStage.VALIDATE.value}",
        "build_research",
        "build_mindmap_guidance",
        "validate_stage_worker",
        "persist_messages",
        "postprocess",
        "apply_updates",
    ]


@pytest.mark.asyncio
async def test_graph_routes_manage_adr_stage_through_dedicated_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []

    async def fake_load_state(_state, _db):
        call_order.append("load_state")
        return {
            "current_project_state": {
                "requirements": [{"id": "req-1", "text": "Capture architectural decisions"}],
                "adrs": [],
            }
        }

    def fake_classify_stage(_state):
        call_order.append("classify_stage")
        return {"next_stage": ProjectStage.MANAGE_ADR.value}

    async def fake_build_summary(state, _db):
        call_order.append(f"build_summary:{state.get('next_stage')}")
        return {"context_summary": "summary"}

    async def fake_build_research(_state):
        call_order.append("build_research")
        return {
            "research_plan": ["Azure data store trade-offs"],
            "stage_directives": "adr stage",
            "mindmap_guidance": None,
        }

    async def fake_research_worker(_state):
        raise AssertionError("research worker should be skipped for manage_adr stage")

    def fake_build_mindmap_guidance(_state):
        call_order.append("build_mindmap_guidance")
        return {"mindmap_guidance": None}

    async def fake_manage_adr_stage_worker(state, _db):
        call_order.append("manage_adr_stage_worker")
        assert state.get("next_stage") == ProjectStage.MANAGE_ADR.value
        return {
            "agent_output": "ADR drafting complete. I created pending change set `cs-adr-1` with 1 ADR draft(s).",
            "intermediate_steps": [],
            "success": True,
            "error": None,
            "handled_by_stage_worker": True,
        }

    async def fake_run_agent(_state):
        raise AssertionError("generic agent should be skipped for manage_adr stage")

    async def fake_persist_messages(_state, _db):
        call_order.append("persist_messages")
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
        "execute_manage_adr_stage_worker_node",
        fake_manage_adr_stage_worker,
    )
    monkeypatch.setattr(graph_factory_module, "run_agent_node", fake_run_agent)
    monkeypatch.setattr(graph_factory_module, "persist_messages_node", fake_persist_messages)
    monkeypatch.setattr(graph_factory_module, "should_route_to_cost_estimator", lambda _state: False)
    monkeypatch.setattr(
        graph_factory_module,
        "get_app_settings",
        lambda: SimpleNamespace(aaa_thread_memory_enabled=False),
    )

    graph = build_project_chat_graph(db=MagicMock())

    result = await graph.ainvoke(
        {
            "project_id": "proj-1",
            "user_message": "Create an ADR for the database decision",
            "success": False,
        }
    )

    assert "cs-adr-1" in result["agent_output"]
    assert call_order == [
        "load_state",
        "classify_stage",
        f"build_summary:{ProjectStage.MANAGE_ADR.value}",
        "build_research",
        "build_mindmap_guidance",
        "manage_adr_stage_worker",
        "persist_messages",
    ]


class _EvaluatorStub:
    def __init__(self, *, result: dict[str, object]) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def evaluate(self, state: dict[str, object]) -> dict[str, object]:
        self.calls.append(state)
        return self.result


class _FindingsWorkerStub:
    def __init__(self, *, result: dict[str, object]) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def generate_findings(
        self,
        *,
        evaluator_result: dict[str, object],
        architecture_state: dict[str, object],
    ) -> dict[str, object]:
        self.calls.append(
            {
                "evaluator_result": evaluator_result,
                "architecture_state": architecture_state,
            }
        )
        return self.result


class _ValidationToolStub:
    def __init__(self, *, response: str) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def _run(self, payload: dict[str, object]) -> str:
        self.calls.append(payload)
        return self.response


class _PromptLoaderStub:
    def load_prompt(self, prompt_name: str, force_reload: bool = False) -> dict[str, str]:
        assert prompt_name == "waf_validator.yaml"
        return {"system_prompt": "Generate remediation-focused WAF findings as JSON."}


@pytest.mark.asyncio
async def test_validate_stage_worker_builds_validation_tool_payload() -> None:
    project_state = {
        "candidateArchitectures": [
            {"id": "candidate-1", "notes": "The app exposes a public endpoint without a WAF."}
        ],
        "referenceDocuments": [
            {
                "id": "doc-1",
                "title": "Azure WAF guidance",
                "url": "https://learn.microsoft.com/azure/well-architected/security/",
            }
        ],
        "wafChecklist": {
            "items": [
                {
                    "id": "sec-waf-1",
                    "pillar": "Security",
                    "topic": "Protect public entry points with a web application firewall",
                }
            ]
        },
    }
    evaluator = _EvaluatorStub(
        result={
            "items": [
                {
                    "itemId": "sec-waf-1",
                    "pillar": "Security",
                    "topic": "Protect public entry points with a web application firewall",
                    "status": "open",
                    "coverageScore": 0.0,
                    "matchedSourcePaths": ["referenceDocuments[0].title"],
                    "evidence": [],
                }
            ],
            "summary": {"evaluatedItems": 1, "sourceCount": 2},
        }
    )
    findings_worker = _FindingsWorkerStub(
        result={
            "findings": [
                {
                    "id": "finding-sec-waf-1",
                    "title": "Public ingress is missing a web application firewall",
                    "severity": "critical",
                    "description": "Traffic reaches the workload without a WAF control.",
                    "remediation": "Add Front Door WAF before production.",
                    "impactedComponents": ["App Service"],
                    "wafPillar": "Security",
                    "wafTopic": "Protect public entry points with a web application firewall",
                    "wafChecklistItemId": "sec-waf-1",
                    "sourceCitations": [
                        {
                            "id": "cite-doc-1",
                            "kind": "referenceDocument",
                            "referenceDocumentId": "doc-1",
                            "url": "https://learn.microsoft.com/azure/well-architected/security/",
                        }
                    ],
                }
            ],
            "wafEvaluations": [
                {
                    "itemId": "sec-waf-1",
                    "pillar": "Security",
                    "topic": "Protect public entry points with a web application firewall",
                    "status": "open",
                    "evidence": "Deterministic WAF evaluator marked this checklist item as open (coverageScore=0.0).",
                    "relatedFindingIds": ["finding-sec-waf-1"],
                    "sourceCitations": [
                        {
                            "id": "cite-doc-1",
                            "kind": "referenceDocument",
                            "referenceDocumentId": "doc-1",
                            "url": "https://learn.microsoft.com/azure/well-architected/security/",
                        }
                    ],
                }
            ],
        }
    )
    validation_tool = _ValidationToolStub(
        response=(
            "Recorded validation results at 2026-04-08T12:00:00+00:00 (findings=1, wafEvaluations=1).\n\n"
            "AAA_STATE_UPDATE\n"
            "```json\n"
            "{\n"
            '  "findings": [{"id": "finding-sec-waf-1"}],\n'
            '  "wafChecklist": {"items": [{"id": "sec-waf-1"}]}\n'
            "}\n"
            "```"
        )
    )

    result = await execute_validate_stage_worker_node(
        {
            "project_id": "proj-1",
            "user_message": "Validate this architecture against WAF",
            "next_stage": "validate",
            "current_project_state": project_state,
        },
        evaluator=evaluator,
        findings_worker=findings_worker,
        validation_tool=validation_tool,
    )

    assert evaluator.calls == [{"current_project_state": project_state}]
    assert findings_worker.calls == [
        {
            "evaluator_result": evaluator.result,
            "architecture_state": project_state,
        }
    ]
    assert validation_tool.calls == [findings_worker.result]
    assert result["agent_output"] == validation_tool.response
    assert result["success"] is True
    assert result["validation_execution_artifact"] == {
        "status": "completed",
        "evaluated_items": 1,
        "actionable_items": 1,
        "findings_generated": 1,
        "waf_evaluations_generated": 1,
    }
    assert result.get("handled_by_stage_worker") is not True


@pytest.mark.asyncio
async def test_validate_stage_worker_skips_when_validation_input_is_insufficient() -> None:
    project_state = {
        "wafChecklist": {
            "items": [
                {
                    "id": "sec-waf-1",
                    "pillar": "Security",
                    "topic": "Protect public entry points with a web application firewall",
                }
            ]
        }
    }
    evaluator = _EvaluatorStub(
        result={
            "items": [
                {
                    "itemId": "sec-waf-1",
                    "pillar": "Security",
                    "topic": "Protect public entry points with a web application firewall",
                    "status": "open",
                    "coverageScore": 0.0,
                    "matchedSourcePaths": [],
                    "evidence": [],
                }
            ],
            "summary": {"evaluatedItems": 1, "sourceCount": 0},
        }
    )
    findings_worker = _FindingsWorkerStub(result={"findings": [], "wafEvaluations": []})
    validation_tool = _ValidationToolStub(response="should not be used")

    result = await execute_validate_stage_worker_node(
        {
            "project_id": "proj-1",
            "user_message": "Validate this architecture against WAF",
            "next_stage": "validate",
            "current_project_state": project_state,
        },
        evaluator=evaluator,
        findings_worker=findings_worker,
        validation_tool=validation_tool,
    )

    assert evaluator.calls == [{"current_project_state": project_state}]
    assert findings_worker.calls == []
    assert validation_tool.calls == []
    assert result["success"] is True
    assert "insufficient" in result["agent_output"].lower()
    assert result["validation_execution_artifact"] == {
        "status": "skipped",
        "reason": "insufficient_input",
        "evaluated_items": 1,
        "source_count": 0,
    }


@pytest.mark.asyncio
async def test_validate_stage_worker_skips_non_validate_turns() -> None:
    result = await execute_validate_stage_worker_node(
        {
            "project_id": "proj-1",
            "user_message": "Continue",
            "next_stage": "clarify",
            "current_project_state": {},
        }
    )

    assert result == {}


@pytest.mark.asyncio
async def test_validate_stage_worker_preserves_stable_finding_ids_across_repeated_runs() -> None:
    project_state = {
        "referenceDocuments": [
            {
                "id": "doc-dns",
                "title": "Private endpoint DNS guidance",
                "url": "https://learn.microsoft.com/azure/private-link/private-endpoint-dns",
            }
        ]
    }
    evaluator = _EvaluatorStub(
        result={
            "items": [
                {
                    "itemId": "rel-dns-1",
                    "pillar": "Reliability",
                    "topic": "Ensure private DNS resolution for private endpoints",
                    "status": "in_progress",
                    "coverageScore": 0.5,
                    "matchedSourcePaths": ["referenceDocuments[0].title"],
                    "evidence": [],
                }
            ],
            "summary": {"evaluatedItems": 1, "sourceCount": 1},
        }
    )

    async def _generator(system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return {
            "findings": [
                {
                    "title": "Missing private DNS coverage",
                    "severity": "medium",
                    "description": "Private endpoints are present but DNS integration is undocumented.",
                    "remediation": "Add private DNS zones and document ownership.",
                    "impactedComponents": ["Private endpoint DNS"],
                    "wafPillar": "Reliability",
                    "wafTopic": "Ensure private DNS resolution for private endpoints",
                    "wafChecklistItemId": "rel-dns-1",
                    "sourceCitations": [
                        {
                            "id": "cite-doc-dns",
                            "kind": "referenceDocument",
                            "referenceDocumentId": "doc-dns",
                            "url": "https://learn.microsoft.com/azure/private-link/private-endpoint-dns",
                        }
                    ],
                }
            ]
        }

    findings_worker = WAFFindingsWorker(
        generator=_generator,
        prompt_loader=_PromptLoaderStub(),
    )
    validation_tool = _ValidationToolStub(response="validation recorded")

    first = await execute_validate_stage_worker_node(
        {
            "project_id": "proj-1",
            "user_message": "Validate this architecture against WAF",
            "next_stage": "validate",
            "current_project_state": project_state,
        },
        evaluator=evaluator,
        findings_worker=findings_worker,
        validation_tool=validation_tool,
    )
    second = await execute_validate_stage_worker_node(
        {
            "project_id": "proj-1",
            "user_message": "Validate this architecture against WAF",
            "next_stage": "validate",
            "current_project_state": project_state,
        },
        evaluator=evaluator,
        findings_worker=findings_worker,
        validation_tool=validation_tool,
    )

    assert first["success"] is True
    assert second["success"] is True
    assert validation_tool.calls[0]["findings"][0]["id"] == "finding-rel-dns-1"
    assert validation_tool.calls[1]["findings"][0]["id"] == "finding-rel-dns-1"
    assert validation_tool.calls[0]["wafEvaluations"][0]["relatedFindingIds"] == ["finding-rel-dns-1"]
    assert validation_tool.calls[1]["wafEvaluations"][0]["relatedFindingIds"] == ["finding-rel-dns-1"]


@pytest.mark.asyncio
async def test_validate_stage_worker_surfaces_missing_actionable_findings_error() -> None:
    evaluator = _EvaluatorStub(
        result={
            "items": [
                {
                    "itemId": "sec-waf-1",
                    "pillar": "Security",
                    "topic": "Protect public entry points with a web application firewall",
                    "status": "open",
                    "coverageScore": 0.0,
                    "matchedSourcePaths": ["referenceDocuments[0].title"],
                    "evidence": [],
                },
                {
                    "itemId": "sec-net-2",
                    "pillar": "Security",
                    "topic": "Restrict lateral network movement",
                    "status": "in_progress",
                    "coverageScore": 0.3,
                    "matchedSourcePaths": ["referenceDocuments[0].title"],
                    "evidence": [],
                },
            ],
            "summary": {"evaluatedItems": 2, "sourceCount": 1},
        }
    )

    async def _generator(system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return {
            "findings": [
                {
                    "title": "Only one gap returned",
                    "severity": "high",
                    "description": "The model forgot the second actionable item.",
                    "remediation": "Return findings for every actionable item.",
                    "impactedComponents": ["App Service"],
                    "wafPillar": "Security",
                    "wafTopic": "Protect public entry points with a web application firewall",
                    "wafChecklistItemId": "sec-waf-1",
                    "sourceCitations": [
                        {
                            "id": "cite-doc-1",
                            "kind": "referenceDocument",
                            "referenceDocumentId": "doc-1",
                            "url": "https://learn.microsoft.com/azure/well-architected/security/",
                        }
                    ],
                }
            ]
        }

    findings_worker = WAFFindingsWorker(
        generator=_generator,
        prompt_loader=_PromptLoaderStub(),
    )
    validation_tool = _ValidationToolStub(response="should not be used")

    result = await execute_validate_stage_worker_node(
        {
            "project_id": "proj-1",
            "user_message": "Validate this architecture against WAF",
            "next_stage": "validate",
            "current_project_state": {
                "referenceDocuments": [
                    {
                        "id": "doc-1",
                        "title": "Security guidance",
                        "url": "https://learn.microsoft.com/azure/well-architected/security/",
                    }
                ]
            },
        },
        evaluator=evaluator,
        findings_worker=findings_worker,
        validation_tool=validation_tool,
    )

    assert result["success"] is False
    assert result["error"] is not None
    assert "missing findings for actionable checklist items: sec-net-2" in result["error"]
    assert result["agent_output"] is not None
    assert "missing findings for actionable checklist items: sec-net-2" in result["agent_output"]
    assert validation_tool.calls == []

