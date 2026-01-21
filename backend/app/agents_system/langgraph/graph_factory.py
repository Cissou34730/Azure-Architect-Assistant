"""
Graph factory for building and compiling the project chat graph.

Wires together nodes and edges into a LangGraph workflow.
"""

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from .nodes.agent import run_agent_node
from .nodes.context import build_context_summary_node, load_project_state_node
from .nodes.persist import apply_state_updates_node, persist_messages_node
from .nodes.postprocess import postprocess_node
from .nodes.research import build_research_plan_node
from .state import GraphState


def build_project_chat_graph(db: AsyncSession | None = None, response_message_id: str = "") -> StateGraph:
    """Build and compile the project chat graph."""
    workflow = StateGraph(GraphState)

    # Use partials or wrapper functions to bind dependencies
    workflow.add_node("load_state", _wrap_load_state(db))
    workflow.add_node("build_summary", _wrap_build_summary(db))
    workflow.add_node("build_research", build_research_plan_node)
    workflow.add_node("run_agent", _wrap_run_agent(db))
    workflow.add_node("postprocess", _wrap_postprocess(response_message_id))
    workflow.add_node("persist_messages", _wrap_persist_messages(db))
    workflow.add_node("apply_updates", _wrap_apply_updates(db))

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


def _wrap_load_state(db: AsyncSession | None):
    async def load_state(state: GraphState) -> dict:
        if db is None:
            return {"current_project_state": {}, "success": True}
        return await load_project_state_node(state, db)
    return load_state


def _wrap_build_summary(db: AsyncSession | None):
    async def build_summary(state: GraphState) -> dict:
        if db is None:
            return {"context_summary": None}
        return await build_context_summary_node(state, db)
    return build_summary


def _wrap_run_agent(db: AsyncSession | None):
    async def run_agent(state: GraphState) -> dict:
        if db is None:
            return {"agent_output": "", "intermediate_steps": [], "success": True, "error": None}
        return await run_agent_node(state)
    return run_agent


def _wrap_postprocess(response_message_id: str):
    async def postprocess(state: GraphState) -> dict:
        return await postprocess_node(state, response_message_id)
    return postprocess


def _wrap_persist_messages(db: AsyncSession | None):
    async def persist_messages(state: GraphState) -> dict:
        if db is None:
            return {}
        return await persist_messages_node(state, db)
    return persist_messages


def _wrap_apply_updates(db: AsyncSession | None):
    async def apply_updates(state: GraphState) -> dict:
        if db is None:
            return {}
        return await apply_state_updates_node(state, db)
    return apply_updates

