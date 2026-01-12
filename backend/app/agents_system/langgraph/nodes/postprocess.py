"""
Post-processing nodes for LangGraph workflow.

Extracts state updates, derives MCP logs, and detects architect choice requirements.
"""

import logging
import re
from typing import Any, Dict, Optional

from ...services.state_update_parser import extract_state_updates
from ...services.iteration_logging import (
    derive_mcp_query_updates_from_steps,
    build_iteration_event_update,
)
from ..state import GraphState

logger = logging.getLogger(__name__)

_AAA_STATE_UPDATE_MARKER = "AAA_STATE_UPDATE"
_ARCHITECT_CHOICE_MARKER_RE = re.compile(
    r"architect\s+choice\s+required\s*:", re.IGNORECASE
)


def _extract_architect_choice_required_section(text: str) -> Optional[str]:
    """Extract architect choice required section from agent output."""
    if not text:
        return None

    match = _ARCHITECT_CHOICE_MARKER_RE.search(text)
    if not match:
        return None

    start = match.start()
    end = text.find(_AAA_STATE_UPDATE_MARKER, start)
    if end < 0:
        end = len(text)

    section = text[start:end].strip()
    if not section:
        return None

    # Avoid bloating ProjectState.openQuestions
    return section[:1500]


async def postprocess_node(state: GraphState, response_message_id: str) -> Dict[str, Any]:
    """
    Post-process agent output to extract updates and detect architect choices.
    
    Args:
        state: Current graph state
        response_message_id: ID of the agent response message for iteration logging
        
    Returns:
        State update with:
        - architect_choice_required_section
        - state_updates (from AAA_STATE_UPDATE)
        - derived_updates (MCP logs + iteration events)
        - combined_updates
    """
    agent_output = state.get("agent_output", "")
    intermediate_steps = state.get("intermediate_steps", [])
    user_message = state.get("user_message", "")
    current_project_state = state.get("current_project_state", {})
    
    # 1) Check for architect choice requirement
    architect_choice_required = _extract_architect_choice_required_section(agent_output)
    if architect_choice_required:
        logger.warning("Architect choice required detected; will block state updates")
    
    # 2) Extract state updates from AAA_STATE_UPDATE blocks
    state_updates = extract_state_updates(agent_output, user_message, current_project_state)
    
    # FR-018: Block state updates if architect choice is required
    if architect_choice_required:
        state_updates = None
    
    # 3) Derive MCP query logging from intermediate steps
    derived_updates: Dict[str, Any] = derive_mcp_query_updates_from_steps(
        intermediate_steps=intermediate_steps,
        user_message=user_message,
    )
    
    mcp_queries_count = 0
    if isinstance(derived_updates, dict) and isinstance(derived_updates.get("mcpQueries"), list):
        mcp_queries_count = len(derived_updates.get("mcpQueries"))
    if mcp_queries_count:
        logger.info(f"Derived {mcp_queries_count} MCP queries")
    
    # 4) Combine state updates with derived updates
    combined_updates: Dict[str, Any] = {}
    for src in [state_updates or {}, derived_updates or {}]:
        for key, value in src.items():
            if key not in combined_updates:
                combined_updates[key] = value
                continue
            if isinstance(combined_updates[key], list) and isinstance(value, list):
                combined_updates[key] = [*combined_updates[key], *value]
            elif isinstance(combined_updates[key], dict) and isinstance(value, dict):
                combined_updates[key] = {**combined_updates[key], **value}
    
    # 5) Add architect choice to openQuestions if detected
    if architect_choice_required:
        combined_updates.setdefault("openQuestions", [])
        if isinstance(combined_updates["openQuestions"], list):
            combined_updates["openQuestions"].append(architect_choice_required)
    
    # 6) Add iteration event
    mcp_query_ids = [
        q.get("id")
        for q in combined_updates.get("mcpQueries", [])
        if isinstance(q, dict) and q.get("id")
    ]
    
    # Determine iteration kind
    kind = (
        "challenge"
        if any(
            k in user_message.lower()
            for k in ["validate", "validation", "waf", "risk", "security benchmark"]
        )
        else "propose"
    )
    
    event_text = agent_output.strip()[:800]
    iteration_update = build_iteration_event_update(
        kind=kind,
        text=event_text,
        mcp_query_ids=[str(qid) for qid in mcp_query_ids if qid],
        architect_response_message_id=response_message_id,
    )
    
    # Merge iteration update into combined updates
    for key, value in iteration_update.items():
        if key not in combined_updates:
            combined_updates[key] = value
        elif isinstance(combined_updates[key], list) and isinstance(value, list):
            combined_updates[key] = [*combined_updates[key], *value]
    
    logger.info(
        f"Post-processing complete: combined_updates keys={sorted(combined_updates.keys())}"
    )
    
    return {
        "architect_choice_required_section": architect_choice_required,
        "state_updates": state_updates,
        "derived_updates": derived_updates,
        "combined_updates": combined_updates,
    }
