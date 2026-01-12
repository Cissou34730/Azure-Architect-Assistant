"""
Agent execution node for LangGraph workflow.

Phase 2: Wraps existing MCPReActAgent execution to preserve behavior.
"""

import logging
from typing import Any, Dict

from ...runner import get_agent_runner
from ..state import GraphState

logger = logging.getLogger(__name__)


async def run_agent_node(state: GraphState) -> Dict[str, Any]:
    """
    Execute agent with project context.
    
    Phase 2: Calls existing runner/orchestrator to preserve behavior.
    Later phases will replace with LangGraph-native tool loop.
    
    Args:
        state: Current graph state
        
    Returns:
        State update with agent output and intermediate steps
    """
    user_message = state["user_message"]
    context_summary = state.get("context_summary")
    
    try:
        # Get the agent runner
        runner = await get_agent_runner()
        
        # Execute with project context
        logger.info(f"Executing agent for message: {user_message[:100]}...")
        result = await runner.execute_query(
            user_message,
            project_context=context_summary,
        )
        
        agent_output = result.get("output", "")
        intermediate_steps = result.get("intermediate_steps", [])
        success = result.get("success", False)
        error = result.get("error")
        
        logger.info(
            f"Agent execution finished (success={success}, steps={len(intermediate_steps)})"
        )
        
        return {
            "agent_output": agent_output,
            "intermediate_steps": intermediate_steps,
            "success": success,
            "error": error,
        }
        
    except RuntimeError as e:
        logger.error(f"Agent not initialized: {e}")
        return {
            "agent_output": "",
            "intermediate_steps": [],
            "success": False,
            "error": f"Agent system not initialized: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        return {
            "agent_output": "",
            "intermediate_steps": [],
            "success": False,
            "error": f"Agent execution failed: {str(e)}",
        }
