"""
Graph factory with Phase 4-6 features.

Builds graphs with stage routing, retry logic, and multi-agent support.
"""

import logging
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.config.app_settings import get_app_settings

from .nodes.agent import run_agent_node
from .nodes.context import build_context_summary_node, load_project_state_node
from .nodes.cost_estimator import cost_estimator_node
from .nodes.extract_requirements import execute_extract_requirements_node
from .nodes.architecture_planner import architecture_planner_node
from .nodes.multi_agent import (
    adr_specialist_node,
    iac_specialist_node,
    pricing_specialist_node,
    route_to_specialist,
    supervisor_node,
    validation_specialist_node,
)
from .nodes.persist import apply_state_updates_node, persist_messages_node
from .nodes.postprocess import postprocess_node
from .nodes.research import build_research_plan_node, execute_research_worker_node
from .nodes.routing import (
    prepare_architecture_planner_handoff,
    prepare_cost_estimator_handoff,
    should_route_to_cost_estimator,
)
from .nodes.stage_routing import (
    ProjectStage,
    build_retry_prompt,
    check_for_retry,
    classify_next_stage,
    propose_next_step,
)
from .state import GraphState

logger = logging.getLogger(__name__)


def build_project_chat_graph(
    db: AsyncSession,
    response_message_id: str = "",
    enable_stage_routing: bool = False,
    enable_multi_agent: bool = False,
) -> StateGraph:
    """Build project chat graph with Phase 4-6 features."""
    workflow = StateGraph(GraphState)

    # Core nodes (all phases)
    workflow.add_node("load_state", _wrap_load_state(db))
    workflow.add_node("build_summary", _wrap_build_summary(db))
    workflow.add_node("classify_stage", classify_next_stage)
    workflow.add_node("extract_requirements", _wrap_extract_requirements(db))
    workflow.add_node("build_research", build_research_plan_node)
    workflow.add_node("research_worker", execute_research_worker_node)
    workflow.add_node("build_mindmap_guidance", _pass_through_mindmap_guidance)
    workflow.add_node("prepare_architecture_handoff", prepare_architecture_planner_handoff)
    workflow.add_node("architecture_planner", architecture_planner_node)
    workflow.add_node("prepare_cost_handoff", prepare_cost_estimator_handoff)
    workflow.add_node("cost_estimator", cost_estimator_node)
    workflow.add_node("run_agent", _wrap_run_agent(db))
    workflow.add_node("persist_messages", _wrap_persist_messages(db))
    workflow.add_node("postprocess", _wrap_postprocess(response_message_id))
    workflow.add_node("apply_updates", _wrap_apply_updates(db))

    # Optional Feature Nodes
    _add_optional_nodes(workflow, enable_stage_routing, enable_multi_agent)

    # Build workflow
    _build_workflow_edges(workflow, enable_stage_routing, enable_multi_agent)

    # Add checkpointer for thread-scoped memory when enabled
    settings = get_app_settings()
    checkpointer = MemorySaver() if settings.aaa_thread_memory_enabled else None

    return workflow.compile(checkpointer=checkpointer)


def _wrap_load_state(db: AsyncSession):
    async def load_state(state: GraphState) -> dict:
        return await load_project_state_node(state, db)
    return load_state


def _wrap_build_summary(db: AsyncSession):
    async def build_summary(state: GraphState) -> dict:
        return await build_context_summary_node(state, db)
    return build_summary


def _wrap_postprocess(response_message_id: str):
    async def postprocess(state: GraphState) -> dict:
        return await postprocess_node(state, response_message_id)
    return postprocess


def _wrap_extract_requirements(db: AsyncSession):
    async def extract_requirements(state: GraphState) -> dict:
        return await execute_extract_requirements_node(state, db)
    return extract_requirements


def _wrap_persist_messages(db: AsyncSession):
    async def persist_messages(state: GraphState) -> dict:
        return await persist_messages_node(state, db)
    return persist_messages


def _wrap_apply_updates(db: AsyncSession):
    async def apply_updates(state: GraphState) -> dict:
        return await apply_state_updates_node(state, db)
    return apply_updates


def _wrap_run_agent(db: AsyncSession):
    async def run_agent(state: GraphState) -> dict:
        return await run_agent_node(state)
    return run_agent


def _pass_through_mindmap_guidance(state: GraphState) -> dict:
    """Dedicated step to make mindmap guidance explicit in graph flow."""
    return {
        "mindmap_guidance": state.get("mindmap_guidance"),
    }


def _add_optional_nodes(workflow: StateGraph, enable_stage_routing: bool, enable_multi_agent: bool):
    """Add Phase 5/6 nodes to the graph if enabled."""
    if enable_stage_routing:
        workflow.add_node("retry_prompt", build_retry_prompt)
        workflow.add_node("propose_next_step", propose_next_step)

    if enable_multi_agent:
        workflow.add_node("supervisor", supervisor_node)
        workflow.add_node("adr_specialist", adr_specialist_node)
        workflow.add_node("validation_specialist", validation_specialist_node)
        workflow.add_node("pricing_specialist", pricing_specialist_node)
        workflow.add_node("iac_specialist", iac_specialist_node)


def _build_workflow_edges(workflow: StateGraph, enable_stage_routing: bool, enable_multi_agent: bool):
    """Define edges and conditional paths for the graph."""
    def route_after_summary(state: GraphState) -> Literal["extract_requirements", "build_research"]:
        if state.get("next_stage") == ProjectStage.EXTRACT_REQUIREMENTS.value:
            return "extract_requirements"
        return "build_research"

    def route_after_research_plan(
        state: GraphState,
    ) -> Literal["research_worker", "build_mindmap_guidance"]:
        if (
            state.get("next_stage") == ProjectStage.PROPOSE_CANDIDATE.value
            and state.get("research_plan")
        ):
            return "research_worker"
        return "build_mindmap_guidance"

    def route_after_research(
        state: GraphState,
    ) -> Literal["cost_estimator", "architecture_planner", "supervisor", "run_agent"]:
        if should_route_to_cost_estimator(state):
            return "cost_estimator"
        if state.get("next_stage") == ProjectStage.PROPOSE_CANDIDATE.value:
            return "architecture_planner"
        return "supervisor" if enable_multi_agent else "run_agent"

    def route_after_persist(state: GraphState) -> Literal["end", "postprocess"]:
        if state.get("handled_by_stage_worker"):
            return "end"
        return "postprocess"

    workflow.set_entry_point("load_state")
    workflow.add_edge("load_state", "classify_stage")
    workflow.add_edge("classify_stage", "build_summary")
    workflow.add_conditional_edges(
        "build_summary",
        route_after_summary,
        {
            "extract_requirements": "extract_requirements",
            "build_research": "build_research",
        },
    )
    workflow.add_edge("extract_requirements", "persist_messages")
    workflow.add_conditional_edges(
        "build_research",
        route_after_research_plan,
        {
            "research_worker": "research_worker",
            "build_mindmap_guidance": "build_mindmap_guidance",
        },
    )
    research_routes = {
        "architecture_planner": "prepare_architecture_handoff",
        "cost_estimator": "prepare_cost_handoff",
        "run_agent": "run_agent",
    }
    if enable_multi_agent:
        research_routes["supervisor"] = "supervisor"

    workflow.add_edge("research_worker", "build_mindmap_guidance")
    workflow.add_conditional_edges("build_mindmap_guidance", route_after_research, research_routes)
    workflow.add_edge("prepare_architecture_handoff", "architecture_planner")
    workflow.add_edge("architecture_planner", "persist_messages")
    workflow.add_edge("prepare_cost_handoff", "cost_estimator")
    workflow.add_edge("cost_estimator", "persist_messages")

    if enable_multi_agent:
        workflow.add_conditional_edges(
            "supervisor",
            route_to_specialist,
            {
                "adr": "adr_specialist",
                "validation": "validation_specialist",
                "pricing": "pricing_specialist",
                "iac": "iac_specialist",
                "general": "run_agent",
            },
        )
        for node in ["adr_specialist", "validation_specialist", "pricing_specialist", "iac_specialist"]:
            workflow.add_edge(node, "run_agent")

    workflow.add_edge("run_agent", "persist_messages")
    workflow.add_conditional_edges(
        "persist_messages",
        route_after_persist,
        {"end": END, "postprocess": "postprocess"},
    )

    if enable_stage_routing:
        workflow.add_conditional_edges(
            "postprocess",
            check_for_retry,
            {"retry": "retry_prompt", "continue": "apply_updates"},
        )
        workflow.add_edge("retry_prompt", END)
        workflow.add_edge("apply_updates", "propose_next_step")
        workflow.add_edge("propose_next_step", END)
    else:
        workflow.add_edge("postprocess", "apply_updates")
        workflow.add_edge("apply_updates", END)

