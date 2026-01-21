"""
Context loading nodes for LangGraph workflow.

Wraps existing project context services.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...services.mindmap_loader import (
    compute_top_level_coverage,
    get_mindmap,
    is_mindmap_initialized,
)
from ...services.project_context import (
    get_project_context_summary,
    read_project_state,
)
from ..state import GraphState

logger = logging.getLogger(__name__)


async def load_project_state_node(
    state: GraphState, db: AsyncSession
) -> dict[str, Any]:
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
                "mindmap": get_mindmap() if is_mindmap_initialized() else None,
                "mindmap_coverage": None,
                "error": f"Project state not found for {project_id}",
                "success": False,
            }

        mindmap = get_mindmap() if is_mindmap_initialized() else None
        mindmap_cov = project_state.get("mindMapCoverage")
        if mindmap_cov is None and mindmap is not None:
            try:
                mindmap_cov = compute_top_level_coverage(project_state)
            except Exception:  # noqa: BLE001
                mindmap_cov = None

        logger.info(f"Loaded project state for {project_id}")
        return {
            "current_project_state": project_state,
            "mindmap": mindmap,
            "mindmap_coverage": mindmap_cov,
            "success": True,
        }

    except Exception as e:
        logger.error(f"Failed to load project state for {project_id}: {e}", exc_info=True)
        return {
            "current_project_state": {},
            "mindmap": get_mindmap() if is_mindmap_initialized() else None,
            "mindmap_coverage": None,
            "error": f"Failed to load project state: {e!s}",
            "success": False,
        }


async def build_context_summary_node(
    state: GraphState, db: AsyncSession
) -> dict[str, Any]:
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
            "error": f"Failed to build context summary: {e!s}",
        }

