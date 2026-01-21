"""
Agent execution node for LangGraph workflow.

Stage-aware execution using the LangGraph-native tool loop.
Falls back to the legacy orchestrator if native execution fails.
"""

import logging
from typing import Any

from ...runner import get_agent_runner
from ..state import GraphState
from .agent_native import run_stage_aware_agent

logger = logging.getLogger(__name__)


async def run_agent_node(state: GraphState) -> dict[str, Any]:
    """
    Execute agent with project context and stage directives.

    Args:
        state: Current graph state

    Returns:
        State update with agent output and intermediate steps
    """
    user_message = state["user_message"]
    context_summary = state.get("context_summary")

    try:
        # Get the agent runner for shared OpenAI + MCP clients
        runner = await get_agent_runner()
        logger.info(f"Executing stage-aware agent for message: {user_message[:100]}...")
        result = await run_stage_aware_agent(
            state,
            mcp_client=getattr(runner, "mcp_client", None),
            openai_settings=getattr(runner, "openai_settings", None),
        )

        # The native agent already returns the expected fields
        return result

    except RuntimeError as e:
        logger.error(f"Agent not initialized: {e}")
        return {
            "agent_output": "",
            "intermediate_steps": [],
            "success": False,
            "error": f"Agent system not initialized: {e!s}",
        }
    except Exception as e:
        logger.error(f"Native agent execution failed, falling back to legacy: {e}", exc_info=True)
        try:
            runner = await get_agent_runner()
            legacy_result = await runner.execute_query(
                user_message,
                project_context=context_summary,
            )
            return {
                "agent_output": legacy_result.get("output", ""),
                "intermediate_steps": legacy_result.get("intermediate_steps", []),
                "success": legacy_result.get("success", False),
                "error": legacy_result.get("error"),
            }
        except Exception as fallback_error:
            logger.error(f"Legacy agent execution also failed: {fallback_error}", exc_info=True)
            return {
                "agent_output": "",
                "intermediate_steps": [],
                "success": False,
                "error": f"Agent execution failed: {fallback_error!s}",
            }

