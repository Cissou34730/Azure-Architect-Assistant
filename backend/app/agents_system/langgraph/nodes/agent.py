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
from .scope_guard import (
    _OUT_OF_SCOPE_REDIRECT,
    is_out_of_scope_request,
    is_probably_in_scope,
    is_scope_refusal,
)
from .waf_shortcuts import (
    build_direct_waf_bulk_update_response,
    build_direct_waf_single_item_update_response,
)

logger = logging.getLogger(__name__)


def _agent_error_result(message: str) -> dict[str, Any]:
    return {
        "agent_output": message,
        "intermediate_steps": [],
        "success": False,
        "error": message,
    }


def _get_shortcut_result(state: GraphState, user_message: str) -> dict[str, Any] | None:
    """Return an immediate result when the request can bypass LLM execution."""
    if is_out_of_scope_request(user_message):
        logger.info("Pre-filter blocked out-of-scope request: %s", user_message[:100])
        return {
            "agent_output": _OUT_OF_SCOPE_REDIRECT,
            "intermediate_steps": [],
            "success": True,
            "error": None,
        }

    single_item_update = build_direct_waf_single_item_update_response(state)
    if single_item_update is not None:
        logger.info(
            "Applying direct WAF single-item update shortcut for message: %s",
            user_message[:80],
        )
        return single_item_update

    direct_update = build_direct_waf_bulk_update_response(state)
    if direct_update is not None:
        logger.info(
            "Applying direct WAF bulk update shortcut for message: %s",
            user_message[:80],
        )
        return direct_update

    return None


async def run_agent_node(state: GraphState, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Execute agent with project context and stage directives.

    Args:
        state: Current graph state

    Returns:
        State update with agent output and intermediate steps
    """
    user_message = state["user_message"]
    event_callback = ((config or {}).get("configurable") or {}).get("event_callback")

    shortcut_result = _get_shortcut_result(state, user_message)
    if shortcut_result is not None:
        return shortcut_result

    try:
        # Get the agent runner for shared OpenAI + MCP clients
        runner = await get_agent_runner()
        logger.info(f"Executing stage-aware agent for message: {user_message[:100]}...")
        result = await run_stage_aware_agent(
            state,
            mcp_client=getattr(runner, "mcp_client", None),
            openai_settings=getattr(runner, "openai_settings", None),
            event_callback=event_callback,
        )
        scope_recovered = await _recover_from_over_refusal(
            result=result,
            state=state,
            runner=runner,
            event_callback=event_callback,
        )
        if scope_recovered is not None:
            return scope_recovered

        # The native agent already returns the expected fields
        return result

    except RuntimeError as e:
        logger.error(f"Agent not initialized: {e}")
        return _agent_error_result(f"Agent system not initialized: {e!s}")
    except Exception as e:
        logger.error(f"Native agent execution failed: {e}", exc_info=True)
        return _agent_error_result(f"LangGraph native agent execution failed: {e!s}")


async def _recover_from_over_refusal(
    *,
    result: dict[str, Any],
    state: GraphState,
    runner: Any,
    event_callback: Any = None,
) -> dict[str, Any] | None:
    """Retry once when a likely in-scope request is incorrectly refused."""
    user_message = str(state.get("user_message", ""))
    agent_output = str(result.get("agent_output", ""))
    if not is_scope_refusal(agent_output):
        return None
    if not is_probably_in_scope(user_message):
        return None

    logger.warning(
        "Detected likely over-refusal for in-scope request; retrying with stronger directives."
    )
    retry_state = dict(state)
    existing_directives = str(retry_state.get("stage_directives", "") or "")
    retry_state["stage_directives"] = (
        existing_directives
        + "\n\nScope override: This user request is in-scope for project/architecture work. "
        "Do NOT refuse. Either perform the requested project update, or ask a focused "
        "clarification question needed to execute it."
    )
    retry_result = await run_stage_aware_agent(
        retry_state,
        mcp_client=getattr(runner, "mcp_client", None),
        openai_settings=getattr(runner, "openai_settings", None),
        event_callback=event_callback,
    )
    retry_output = str(retry_result.get("agent_output", ""))
    if retry_output.strip() and not is_scope_refusal(retry_output):
        return retry_result

    return {
        "agent_output": (
            "This request is in scope for the project assistant. "
            "I can execute it once you confirm the exact target artifact/item if ambiguous."
        ),
        "intermediate_steps": retry_result.get("intermediate_steps", []),
        "success": True,
        "error": None,
    }

