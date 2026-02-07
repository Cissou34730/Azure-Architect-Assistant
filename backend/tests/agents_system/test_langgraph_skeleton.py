"""
Tests for LangGraph skeleton and graph compilation.

Phase 1: Verify basic graph structure can be created and compiled.
"""

import asyncio

from app.agents_system.langgraph.graph_factory import _agent_router_node
from app.agents_system.langgraph.graph_factory import build_project_chat_graph
from app.agents_system.langgraph.state import GraphState


def test_graph_can_be_compiled():
    """Test that the minimal graph can be compiled without errors."""
    graph = build_project_chat_graph()
    assert graph is not None


def test_graph_can_execute_noop():
    """Test that the no-op graph can execute with minimal state."""
    graph = build_project_chat_graph()

    initial_state: GraphState = {
        "project_id": "test-proj-1",
        "user_message": "Hello",
        "success": False,
    }

    result = asyncio.run(graph.ainvoke(initial_state))

    assert result is not None
    assert result.get("success") is True
    assert result.get("project_id") == "test-proj-1"


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


def test_router_prefers_main_agent_for_validate_stage():
    state: GraphState = {
        "user_message": "Let's start creating the WAF checklist now",
        "next_stage": "validate",
        "context_summary": "multi-region high availability compliance",
        "current_project_state": {},
    }

    decision = _agent_router_node(state)

    assert decision["routing_decision"]["agent"] == "main"

