"""
Persistence nodes for LangGraph workflow.

Saves conversation messages and applies state updates to database.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from ...services.project_context import update_project_state
from ...services.iteration_logging import derive_uncovered_topic_questions
from ....models.project import ConversationMessage
from ..state import GraphState

logger = logging.getLogger(__name__)


async def persist_messages_node(
    state: GraphState, db: AsyncSession
) -> Dict[str, Any]:
    """
    Persist user and agent messages to database.
    
    Args:
        state: Current graph state
        db: Database session
        
    Returns:
        State update with message IDs
    """
    project_id = state["project_id"]
    user_message = state["user_message"]
    agent_output = state.get("agent_output", "")
    
    try:
        # Save user message
        user_msg = ConversationMessage(
            id=str(uuid.uuid4()),
            project_id=project_id,
            role="user",
            content=user_message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        db.add(user_msg)
        
        # Save agent response
        agent_msg = ConversationMessage(
            id=str(uuid.uuid4()),
            project_id=project_id,
            role="assistant",
            content=agent_output,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        db.add(agent_msg)
        
        await db.flush()
        
        logger.info(f"Persisted messages for project {project_id}")
        
        return {
            "user_message_id": user_msg.id,
            "agent_message_id": agent_msg.id,
        }
        
    except Exception as e:
        logger.error(f"Failed to persist messages: {e}", exc_info=True)
        return {
            "error": f"Failed to persist messages: {str(e)}",
        }


async def apply_state_updates_node(
    state: GraphState, db: AsyncSession
) -> Dict[str, Any]:
    """
    Apply combined state updates to project state.
    
    Also handles uncovered topics and failed MCP guidance.
    
    Args:
        state: Current graph state
        db: Database session
        
    Returns:
        State update with updated project state and final answer
    """
    project_id = state["project_id"]
    combined_updates = state.get("combined_updates", {})
    agent_output = state.get("agent_output", "")
    architect_choice_required = state.get("architect_choice_required_section")
    
    if not combined_updates:
        logger.info(f"No state updates to apply for project {project_id}")
        return {
            "updated_project_state": state.get("current_project_state"),
            "final_answer": agent_output,
        }
    
    try:
        logger.info(
            f"Applying state updates for project {project_id} (keys={sorted(combined_updates.keys())})"
        )
        
        updated_state = await update_project_state(project_id, combined_updates, db)
        
        # Build final answer with additional guidance
        final_answer = agent_output
        
        # Add uncovered topic prompts if no architect choice required
        if not architect_choice_required:
            uncovered_questions = derive_uncovered_topic_questions(updated_state)
            if uncovered_questions:
                final_answer += "\n\nUncovered topics to confirm:\n" + "\n".join(
                    [f"- {q}" for q in uncovered_questions]
                )
                try:
                    await update_project_state(
                        project_id,
                        {"openQuestions": uncovered_questions},
                        db,
                    )
                except Exception as prompt_update_error:
                    logger.warning(
                        f"Failed to persist openQuestions: {prompt_update_error}"
                    )
        
        # Surface failed MCP lookups (T025)
        failed_mcp_queries: List[str] = []
        for q in (
            combined_updates.get("mcpQueries", [])
            if isinstance(combined_updates.get("mcpQueries"), list)
            else []
        ):
            if not isinstance(q, dict):
                continue
            result_urls = q.get("resultUrls")
            if isinstance(result_urls, list) and len(result_urls) == 0:
                query_text = q.get("queryText")
                if isinstance(query_text, str) and query_text.strip():
                    failed_mcp_queries.append(query_text.strip())
        
        if failed_mcp_queries:
            deduped_failed: List[str] = []
            seen_failed: set[str] = set()
            for qt in failed_mcp_queries:
                if qt not in seen_failed:
                    seen_failed.add(qt)
                    deduped_failed.append(qt)
            
            final_answer += (
                "\n\nMCP lookups returned no results - "
                "please clarify the exact term/service to search for:\n"
            )
            for qt in deduped_failed[:3]:
                final_answer += f"- '{qt}'\n"
        
        logger.info(f"State updates applied successfully for project {project_id}")
        
        return {
            "updated_project_state": updated_state,
            "final_answer": final_answer,
            "success": True,
        }
        
    except Exception as e:
        logger.error(f"Failed to apply state updates: {e}", exc_info=True)
        return {
            "updated_project_state": state.get("current_project_state"),
            "final_answer": agent_output,
            "error": f"Failed to apply state updates: {str(e)}",
            "success": False,
        }
