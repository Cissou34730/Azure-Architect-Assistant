"""
Context loading nodes for LangGraph workflow.

Wraps existing project context services.
"""

import logging
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from ...services.project_context import (
    read_project_state,
    get_project_context_summary,
)
from ..state import GraphState

logger = logging.getLogger(__name__)


async def load_project_state_node(
    state: GraphState, db: AsyncSession
) -> Dict[str, Any]:
    """
    Load project state from database.
    
    Args:
        state: Current graph state
        db: Database session
        
    Returns:
        State update with loaded project state
    """
    project_id = state["project_id"]
    
    try:
        project_state = await read_project_state(project_id, db)
        
        if not project_state:
            logger.warning(f"No project state found for {project_id}")
            return {
                "current_project_state": {},
                "error": f"Project state not found for {project_id}",
                "success": False,
            }
        
        logger.info(f"Loaded project state for {project_id}")
        return {
            "current_project_state": project_state,
            "success": True,
        }
        
    except Exception as e:
        logger.error(f"Failed to load project state for {project_id}: {e}", exc_info=True)
        return {
            "current_project_state": {},
            "error": f"Failed to load project state: {str(e)}",
            "success": False,
        }


async def build_context_summary_node(
    state: GraphState, db: AsyncSession
) -> Dict[str, Any]:
    """
    Build formatted context summary for agent.
    
    Args:
        state: Current graph state
        db: Database session
        
    Returns:
        State update with context summary
    """
    project_id = state["project_id"]
    
    try:
        context_summary = await get_project_context_summary(project_id, db)
        
        logger.info(f"Built context summary for {project_id} ({len(context_summary)} chars)")
        return {
            "context_summary": context_summary,
        }
        
    except Exception as e:
        logger.error(f"Failed to build context summary for {project_id}: {e}", exc_info=True)
        return {
            "context_summary": None,
            "error": f"Failed to build context summary: {str(e)}",
        }
