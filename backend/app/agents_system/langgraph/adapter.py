"""
Adapter for LangGraph project chat execution.

Provides a simple interface matching the router's expectations.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .graph_factory import build_project_chat_graph
from .state import GraphState

logger = logging.getLogger(__name__)


async def execute_project_chat(
    project_id: str,
    user_message: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Execute project-aware chat using LangGraph workflow.
    
    This adapter matches the interface expected by the router so it can be
    used as a drop-in replacement for the existing execution path.
    
    Args:
        project_id: Project ID
        user_message: User's message
        db: Database session
        
    Returns:
        Dictionary with:
        - answer: Final answer (str)
        - success: Whether execution succeeded (bool)
        - project_state: Updated project state (dict, optional)
        - reasoning_steps: Agent reasoning steps (list, optional)
        - error: Error message if failed (str, optional)
    """
    try:
        # Generate message ID for iteration logging
        response_message_id = str(uuid.uuid4())
        
        # Build and compile graph
        graph = build_project_chat_graph(db, response_message_id)
        
        # Initialize state
        initial_state: GraphState = {
            "project_id": project_id,
            "user_message": user_message,
            "success": False,
        }
        
        logger.info(f"Executing LangGraph workflow for project {project_id}")
        
        # Execute graph
        result_state = await graph.ainvoke(initial_state)
        
        # Extract response fields
        final_answer = result_state.get("final_answer", "")
        success = result_state.get("success", False)
        updated_state = result_state.get("updated_project_state")
        error = result_state.get("error")
        
        # Format intermediate steps (for compatibility with router)
        reasoning_steps = []
        intermediate_steps = result_state.get("intermediate_steps", [])
        for step in intermediate_steps:
            if isinstance(step, tuple) and len(step) == 2:
                action, observation = step
                reasoning_steps.append({
                    "action": action.tool if hasattr(action, "tool") else str(action),
                    "action_input": (
                        action.tool_input if hasattr(action, "tool_input") else ""
                    ),
                    "observation": str(observation)[:500],
                })
        
        logger.info(
            f"LangGraph execution complete: success={success}, steps={len(reasoning_steps)}"
        )
        
        return {
            "answer": final_answer if final_answer else result_state.get("agent_output", ""),
            "success": success,
            "project_state": updated_state,
            "reasoning_steps": reasoning_steps,
            "error": error,
        }
        
    except Exception as e:
        logger.error(f"LangGraph execution failed: {e}", exc_info=True)
        return {
            "answer": "",
            "success": False,
            "project_state": None,
            "reasoning_steps": [],
            "error": f"Graph execution failed: {str(e)}",
        }
