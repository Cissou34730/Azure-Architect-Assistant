"""
Graph factory for building and compiling the project chat graph.

Wires together nodes and edges into a LangGraph workflow.
"""

from typing import Any
from langgraph.graph import StateGraph, END

from .state import GraphState


def _noop_node(state: GraphState) -> GraphState:
    """Temporary no-op node for initial skeleton testing."""
    return {**state, "success": True}


def build_project_chat_graph() -> StateGraph:
    """
    Build and compile the project chat graph.
    
    Phase 1: Minimal no-op graph for compilation testing.
    Later phases will add real nodes and edges.
    
    Returns:
        Compiled LangGraph workflow.
    """
    workflow = StateGraph(GraphState)
    
    # Phase 1: Single no-op node
    workflow.add_node("noop", _noop_node)
    workflow.set_entry_point("noop")
    workflow.add_edge("noop", END)
    
    return workflow.compile()
