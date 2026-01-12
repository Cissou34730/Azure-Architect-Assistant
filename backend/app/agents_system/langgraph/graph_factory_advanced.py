"""
Advanced graph factory with Phase 4-6 features.

Builds graphs with stage routing, retry logic, and multi-agent support.
"""

import logging
from typing import Any, Optional
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession

from .state import GraphState
from .nodes.context import load_project_state_node, build_context_summary_node
from .nodes.agent import run_agent_node
from .nodes.postprocess import postprocess_node
from .nodes.persist import persist_messages_node, apply_state_updates_node
from .nodes.stage_routing import (
    classify_next_stage,
    check_for_retry,
    build_retry_prompt,
    propose_next_step,
)
from .nodes.multi_agent import (
    supervisor_node,
    adr_specialist_node,
    validation_specialist_node,
    pricing_specialist_node,
    iac_specialist_node,
    route_to_specialist,
)

logger = logging.getLogger(__name__)


def build_advanced_project_chat_graph(
    db: AsyncSession,
    response_message_id: str = "",
    enable_stage_routing: bool = False,
    enable_multi_agent: bool = False,
) -> StateGraph:
    """
    Build advanced project chat graph with Phase 4-6 features.
    
    Args:
        db: Database session
        response_message_id: Message ID for iteration logging
        enable_stage_routing: Enable Phase 5 stage routing and retry
        enable_multi_agent: Enable Phase 6 multi-agent specialists
        
    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(GraphState)
    
    # Define nodes with bound dependencies
    async def load_state(state: GraphState) -> dict:
        return await load_project_state_node(state, db)
    
    async def build_summary(state: GraphState) -> dict:
        return await build_context_summary_node(state, db)
    
    async def run_agent(state: GraphState) -> dict:
        return await run_agent_node(state)
    
    async def postprocess(state: GraphState) -> dict:
        return await postprocess_node(state, response_message_id)
    
    async def persist_messages(state: GraphState) -> dict:
        return await persist_messages_node(state, db)
    
    async def apply_updates(state: GraphState) -> dict:
        return await apply_state_updates_node(state, db)
    
    # Core nodes (all phases)
    workflow.add_node("load_state", load_state)
    workflow.add_node("build_summary", build_summary)
    workflow.add_node("run_agent", run_agent)
    workflow.add_node("persist_messages", persist_messages)
    workflow.add_node("postprocess", postprocess)
    workflow.add_node("apply_updates", apply_updates)
    
    # Phase 5 nodes (stage routing and retry)
    if enable_stage_routing:
        workflow.add_node("classify_stage", classify_next_stage)
        workflow.add_node("retry_prompt", build_retry_prompt)
        workflow.add_node("propose_next_step", propose_next_step)
    
    # Phase 6 nodes (multi-agent)
    if enable_multi_agent:
        workflow.add_node("supervisor", supervisor_node)
        workflow.add_node("adr_specialist", adr_specialist_node)
        workflow.add_node("validation_specialist", validation_specialist_node)
        workflow.add_node("pricing_specialist", pricing_specialist_node)
        workflow.add_node("iac_specialist", iac_specialist_node)
    
    # Build workflow based on enabled features
    workflow.set_entry_point("load_state")
    workflow.add_edge("load_state", "build_summary")
    
    if enable_multi_agent:
        # Phase 6: Route through supervisor
        workflow.add_edge("build_summary", "supervisor")
        workflow.add_conditional_edges(
            "supervisor",
            route_to_specialist,
            {
                "adr": "adr_specialist",
                "validation": "validation_specialist",
                "pricing": "pricing_specialist",
                "iac": "iac_specialist",
                "general": "run_agent",
            }
        )
        # All specialists merge back to persist
        workflow.add_edge("adr_specialist", "persist_messages")
        workflow.add_edge("validation_specialist", "persist_messages")
        workflow.add_edge("pricing_specialist", "persist_messages")
        workflow.add_edge("iac_specialist", "persist_messages")
        workflow.add_edge("run_agent", "persist_messages")
    else:
        workflow.add_edge("build_summary", "run_agent")
        workflow.add_edge("run_agent", "persist_messages")
    
    workflow.add_edge("persist_messages", "postprocess")
    
    if enable_stage_routing:
        # Phase 5: Add retry logic
        workflow.add_edge("postprocess", "classify_stage")
        workflow.add_conditional_edges(
            "classify_stage",
            check_for_retry,
            {
                "retry": "retry_prompt",
                "continue": "apply_updates",
            }
        )
        workflow.add_edge("retry_prompt", END)  # Return to user for clarification
        workflow.add_edge("apply_updates", "propose_next_step")
        workflow.add_edge("propose_next_step", END)
    else:
        workflow.add_edge("postprocess", "apply_updates")
        workflow.add_edge("apply_updates", END)
    
    return workflow.compile()
