"""
Graph factory for building and compiling the project chat graph.

Wires together nodes and edges into a LangGraph workflow.
"""

from typing import Any, Optional
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession

from .state import GraphState
from .nodes.context import load_project_state_node, build_context_summary_node
from .nodes.research import build_research_plan_node
from .nodes.agent import run_agent_node
from .nodes.postprocess import postprocess_node
from .nodes.persist import persist_messages_node, apply_state_updates_node


def build_project_chat_graph(db: Optional[AsyncSession] = None, response_message_id: str = "") -> StateGraph:
    """
    Build and compile the project chat graph.
    
    Phase 2: Full graph with context loading, agent execution, postprocessing,
    and persistence nodes.
    
    Args:
        db: Optional database session for nodes that need database access
        response_message_id: Message ID for iteration logging (generated dynamically)
        
    Returns:
        Compiled LangGraph workflow.
    """
    workflow = StateGraph(GraphState)
    
    # Define nodes with bound dependencies
    async def load_state(state: GraphState) -> dict:
        # If no DB provided (tests / noop mode), return an empty project state
        if db is None:
            return {
                "current_project_state": {},
                "success": True,
            }
        return await load_project_state_node(state, db)
    
    async def build_summary(state: GraphState) -> dict:
        if db is None:
            return {"context_summary": None}
        return await build_context_summary_node(state, db)

    async def build_research(state: GraphState) -> dict:
        return await build_research_plan_node(state)
    
    async def run_agent(state: GraphState) -> dict:
        # In test/noop mode (db is None) don't attempt to run external agent
        if db is None:
            return {
                "agent_output": "",
                "intermediate_steps": [],
                "success": True,
                "error": None,
            }
        return await run_agent_node(state)
    
    async def postprocess(state: GraphState) -> dict:
        return await postprocess_node(state, response_message_id)
    
    async def persist_messages(state: GraphState) -> dict:
        # No-op persistence when running without a DB (tests)
        if db is None:
            return {}
        result = await persist_messages_node(state, db)
        # Update response_message_id for next postprocess call
        # (Note: This is a workaround; proper solution in Phase 3+)
        return result
    
    async def apply_updates(state: GraphState) -> dict:
        if db is None:
            return {}
        return await apply_state_updates_node(state, db)
    
    # Add nodes
    workflow.add_node("load_state", load_state)
    workflow.add_node("build_summary", build_summary)
    workflow.add_node("build_research", build_research)
    workflow.add_node("run_agent", run_agent)
    workflow.add_node("postprocess", postprocess)
    workflow.add_node("persist_messages", persist_messages)
    workflow.add_node("apply_updates", apply_updates)
    
    # Define edges (linear flow for Phase 2)
    workflow.set_entry_point("load_state")
    workflow.add_edge("load_state", "build_summary")
    workflow.add_edge("build_summary", "build_research")
    workflow.add_edge("build_research", "run_agent")
    workflow.add_edge("run_agent", "persist_messages")
    workflow.add_edge("persist_messages", "postprocess")
    workflow.add_edge("postprocess", "apply_updates")
    workflow.add_edge("apply_updates", END)
    
    return workflow.compile()
