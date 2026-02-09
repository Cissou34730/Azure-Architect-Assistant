"""
Agent execution node for LangGraph workflow.

Stage-aware execution using the LangGraph-native tool loop.
Falls back to the legacy orchestrator if native execution fails.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from ...runner import get_agent_runner
from ..state import GraphState
from .agent_native import run_stage_aware_agent

logger = logging.getLogger(__name__)

_PILLAR_ALIASES: dict[str, tuple[str, ...]] = {
    "Reliability": ("reliability", "reliabilty", "reliablity", "resilience", "resiliency"),
    "Security": ("security",),
    "Cost Optimization": ("cost optimization", "cost", "finops"),
    "Operational Excellence": ("operational excellence", "operations"),
    "Performance Efficiency": ("performance efficiency", "performance"),
}


async def run_agent_node(state: GraphState) -> dict[str, Any]:
    """
    Execute agent with project context and stage directives.

    Args:
        state: Current graph state

    Returns:
        State update with agent output and intermediate steps
    """
    user_message = state["user_message"]
    direct_update = _build_direct_waf_bulk_update_response(state)
    if direct_update is not None:
        logger.info("Applying direct WAF bulk update shortcut for message: %s", user_message[:80])
        return direct_update

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
        logger.error(f"Native agent execution failed: {e}", exc_info=True)
        return {
            "agent_output": "",
            "intermediate_steps": [],
            "success": False,
            "error": f"LangGraph native agent execution failed: {e!s}",
        }


def _build_direct_waf_bulk_update_response(state: GraphState) -> dict[str, Any] | None:
    """Build deterministic checklist updates for explicit bulk-completion commands."""
    user_message = str(state.get("user_message", ""))

    target_pillar = _extract_target_pillar(user_message)
    if target_pillar is None:
        return None
    if not _is_bulk_completion_request(user_message):
        return None

    items = _extract_pillar_items(state.get("current_project_state") or {}, target_pillar)
    if not items:
        return None

    timestamp = datetime.now(timezone.utc).isoformat()
    bulk_evidence = (
        f"Manual bulk override requested by user: marked all {target_pillar} checks as covered. "
        "Evidence not independently verified in this turn."
    )
    update_items = [
        {
            "id": item["id"],
            "pillar": target_pillar,
            "topic": item["topic"],
            "evaluations": [
                {
                    "id": str(uuid.uuid4()),
                    "status": "covered",
                    "evidence": bulk_evidence,
                    "relatedFindingIds": [],
                    "sourceCitations": [],
                    "createdAt": timestamp,
                }
            ],
        }
        for item in items
    ]
    state_update = {"wafChecklist": {"items": update_items}}
    response_text = (
        f"Updated {len(update_items)} {target_pillar} WAF checklist items to covered.\n\n"
        "Risk warning: this is a manual bulk override without per-item validation evidence. "
        "Treat it as provisional and verify each control before sign-off.\n\n"
        "AAA_STATE_UPDATE\n"
        "```json\n"
        f"{json.dumps(state_update, ensure_ascii=False, indent=2)}\n"
        "```"
    )
    return {
        "agent_output": response_text,
        "intermediate_steps": [],
        "success": True,
        "error": None,
    }


def _extract_target_pillar(user_message: str) -> str | None:
    lowered = user_message.lower()
    for pillar, aliases in _PILLAR_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return pillar
    return None


def _is_bulk_completion_request(user_message: str) -> bool:
    lowered = user_message.lower()
    completion_terms = ("done", "complete", "completed", "covered", "green")
    scope_terms = ("all", "entire", "every")
    action_terms = ("update", "mark", "set")

    has_completion = any(term in lowered for term in completion_terms)
    has_scope = any(term in lowered for term in scope_terms)
    if not has_completion or not has_scope:
        return False

    has_checklist_ref = "checklist" in lowered or "waf" in lowered
    has_action = any(term in lowered for term in action_terms)
    return has_checklist_ref or has_action


def _extract_pillar_items(current_project_state: dict[str, Any], pillar: str) -> list[dict[str, str]]:
    waf = current_project_state.get("wafChecklist")
    if not isinstance(waf, dict):
        return []

    raw_items = waf.get("items")
    items_iterable = raw_items.values() if isinstance(raw_items, dict) else raw_items
    if not isinstance(items_iterable, (list, tuple)) and not hasattr(items_iterable, "__iter__"):
        return []

    selected: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for item in items_iterable:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "")).strip()
        topic = str(item.get("topic") or item.get("title") or item_id).strip()
        item_pillar = str(item.get("pillar", "")).strip()
        if not item_id or not topic or item_pillar.lower() != pillar.lower():
            continue
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        selected.append({"id": item_id, "topic": topic})
    return selected

