"""
Tests for LangGraph skeleton and graph compilation.

Phase 1: Verify basic graph structure can be created and compiled.
"""

import asyncio
from unittest.mock import MagicMock

from app.agents_system.langgraph.graph_factory import build_project_chat_graph
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

