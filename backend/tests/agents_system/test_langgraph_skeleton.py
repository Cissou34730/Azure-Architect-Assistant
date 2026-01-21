"""
Tests for LangGraph skeleton and graph compilation.

Phase 1: Verify basic graph structure can be created and compiled.
"""

import asyncio

from backend.app.agents_system.langgraph.graph_factory import build_project_chat_graph
from backend.app.agents_system.langgraph.state import GraphState


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

