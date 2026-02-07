"""
Graph factory for building and compiling the project chat graph.

Wires together nodes and edges into a LangGraph workflow.
"""

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from .nodes.agent import run_agent_node
from .nodes.architecture_planner import architecture_planner_node
from .nodes.context import build_context_summary_node, load_project_state_node
from .nodes.cost_estimator import cost_estimator_node
from .nodes.iac_generator import iac_generator_node
from .nodes.persist import apply_state_updates_node, persist_messages_node
from .nodes.postprocess import postprocess_node
from .nodes.research import build_research_plan_node
from .nodes.saas_advisor import saas_advisor_node
from .nodes.stage_routing import (
    classify_next_stage,
    prepare_architecture_planner_handoff,
    prepare_cost_estimator_handoff,
    prepare_iac_generator_handoff,
    prepare_saas_advisor_handoff,
    should_route_to_architecture_planner,
    should_route_to_cost_estimator,
    should_route_to_iac_generator,
    should_route_to_saas_advisor,
)
from .state import GraphState


def build_project_chat_graph(db: AsyncSession | None = None, response_message_id: str = "") -> StateGraph:
    """Build and compile the project chat graph with multi-agent routing."""
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("load_state", _wrap_load_state(db))
    workflow.add_node("build_summary", _wrap_build_summary(db))
    workflow.add_node("classify_stage", classify_next_stage)
    workflow.add_node("build_research", build_research_plan_node)
    workflow.add_node("agent_router", _agent_router_node)
    workflow.add_node("prepare_arch_handoff", prepare_architecture_planner_handoff)
    workflow.add_node("prepare_iac_handoff", prepare_iac_generator_handoff)
    workflow.add_node("prepare_saas_handoff", prepare_saas_advisor_handoff)
    workflow.add_node("prepare_cost_handoff", prepare_cost_estimator_handoff)
    workflow.add_node("architecture_planner", architecture_planner_node)
    workflow.add_node("iac_generator", iac_generator_node)
    workflow.add_node("saas_advisor", saas_advisor_node)
    workflow.add_node("cost_estimator", cost_estimator_node)
    workflow.add_node("run_agent", _wrap_run_agent(db))
    workflow.add_node("persist_messages", _wrap_persist_messages(db))
    workflow.add_node("postprocess", _wrap_postprocess(response_message_id))
    workflow.add_node("apply_updates", _wrap_apply_updates(db))

    # Define edges
    workflow.set_entry_point("load_state")
    workflow.add_edge("load_state", "build_summary")
    workflow.add_edge("build_summary", "classify_stage")
    workflow.add_edge("classify_stage", "build_research")
    workflow.add_edge("build_research", "agent_router")

    # Conditional routing from agent_router
    workflow.add_conditional_edges(
        "agent_router",
        _route_to_agent,
        {
            "architecture_planner": "prepare_arch_handoff",
            "iac_generator": "prepare_iac_handoff",
            "saas_advisor": "prepare_saas_handoff",
            "cost_estimator": "prepare_cost_handoff",
            "main_agent": "run_agent",
        }
    )

    # Architecture Planner flow
    workflow.add_edge("prepare_arch_handoff", "architecture_planner")
    workflow.add_edge("architecture_planner", "persist_messages")

    # IaC Generator flow
    workflow.add_edge("prepare_iac_handoff", "iac_generator")
    workflow.add_edge("iac_generator", "persist_messages")

    # SaaS Advisor flow (Phase 3)
    workflow.add_edge("prepare_saas_handoff", "saas_advisor")
    workflow.add_edge("saas_advisor", "persist_messages")

    # Cost Estimator flow (Phase 3)
    workflow.add_edge("prepare_cost_handoff", "cost_estimator")
    workflow.add_edge("cost_estimator", "persist_messages")

    # Main agent flow
    workflow.add_edge("run_agent", "persist_messages")

    # Common postprocessing flow
    workflow.add_edge("persist_messages", "postprocess")
    workflow.add_edge("postprocess", "apply_updates")
    workflow.add_edge("apply_updates", END)

    return workflow.compile()


def _agent_router_node(state: GraphState) -> dict:
    """Router node that decides which agent to invoke."""
    # Check for IaC generation request first (more specific)
    if should_route_to_iac_generator(state):
        return {
            "routing_decision": {
                "agent": "iac_generator",
                "reason": "IaC generation request with finalized architecture",
            }
        }

    # Check for architecture planning request
    if should_route_to_architecture_planner(state):
        return {
            "routing_decision": {
                "agent": "architecture_planner",
                "reason": "Architecture design request detected",
            }
        }

    # Phase 3: Check for SaaS-specific request (LOW priority)
    if should_route_to_saas_advisor(state):
        return {
            "routing_decision": {
                "agent": "saas_advisor",
                "reason": "SaaS architecture guidance requested",
            }
        }

    # Phase 3: Check for Cost Estimator request (LOWEST priority)
    if should_route_to_cost_estimator(state):
        return {
            "routing_decision": {
                "agent": "cost_estimator",
                "reason": "Cost estimation requested for architecture",
            }
        }

    # Default to main agent
    return {
        "routing_decision": {
            "agent": "main",
            "reason": "Standard conversational interaction",
        }
    }


def _route_to_agent(state: GraphState) -> str:
    """Routing function for conditional edge."""
    routing_decision = state.get("routing_decision", {})
    agent = routing_decision.get("agent", "main")

    agent_routes = {
        "architecture_planner": "architecture_planner",
        "iac_generator": "iac_generator",
        "saas_advisor": "saas_advisor",
        "cost_estimator": "cost_estimator",
    }
    return agent_routes.get(agent, "main_agent")


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

