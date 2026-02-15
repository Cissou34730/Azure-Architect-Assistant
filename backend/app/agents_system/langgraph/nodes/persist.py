"""
Persistence nodes for LangGraph workflow.

Saves conversation messages and applies state updates to database.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ....models.project import ConversationMessage
from ...services.iteration_logging import derive_uncovered_topic_questions
from ...services.project_context import update_project_state
from ...services.response_sanitizer import sanitize_agent_output
from ..state import GraphState

logger = logging.getLogger(__name__)

MAX_UNCOVERED_TOPIC_PROMPTS = 2
MAX_OPEN_QUESTIONS_PERSISTED = 5


async def persist_messages_node(
    state: GraphState, db: AsyncSession
) -> dict[str, Any]:
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
    sanitized_agent_output = sanitize_agent_output(str(agent_output))

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
            content=sanitized_agent_output,
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
            "error": f"Failed to persist messages: {e!s}",
        }


async def apply_state_updates_node(
    state: GraphState, db: AsyncSession
) -> dict[str, Any]:
    """
    Apply combined state updates to project state.

    Also handles uncovered topics and failed MCP guidance.
    """
    project_id = state["project_id"]
    combined_updates = state.get("combined_updates", {})
    agent_output = state.get("agent_output", "")
    architect_choice_required = state.get("architect_choice_required_section")

    if not combined_updates:
        logger.info(f"No state updates to apply for project {project_id}")
        return {
            "updated_project_state": state.get("current_project_state"),
            "final_answer": sanitize_agent_output(str(agent_output)),
        }

    try:
        logger.info(
            f"Applying state updates for project {project_id} (keys={sorted(combined_updates.keys())})"
        )

        updated_state = await update_project_state(project_id, combined_updates, db)

        # NEW: Sync to normalized DB if feature enabled
        try:
            from app.agents_system.checklists.service import get_checklist_service  # noqa: PLC0415
            from app.core.app_settings import get_settings  # noqa: PLC0415

            settings = get_settings()
            if settings.aaa_feature_waf_normalized:
                service = await get_checklist_service(db=db, settings=settings)
                await service.sync_project(
                    project_id=project_id, project_state=updated_state
                )
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to sync project {project_id} to normalized DB: {e}")

        # Build final answer with additional guidance
        final_answer = sanitize_agent_output(str(agent_output))
        final_answer = await _handle_uncovered_topics(
            project_id, updated_state, final_answer, architect_choice_required, db
        )
        final_answer = _handle_failed_mcp_lookups(combined_updates, final_answer)
        final_answer = _handle_waf_followup_guardrail(
            next_stage=state.get("next_stage"),
            combined_updates=combined_updates,
            updated_state=updated_state,
            final_answer=final_answer,
        )

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
            "final_answer": sanitize_agent_output(str(agent_output)),
            "error": f"Failed to apply state updates: {e!s}",
            "success": False,
        }


async def _handle_uncovered_topics(
    project_id: str,
    updated_state: dict[str, Any],
    final_answer: str,
    architect_choice_required: Any,
    db: AsyncSession,
) -> str:
    """Detect and persist uncovered mindmap topics if appropriate."""
    if architect_choice_required:
        return final_answer

    existing_questions = _extract_existing_questions(updated_state)
    uncovered_questions = derive_uncovered_topic_questions(updated_state)
    selected_questions = _select_new_uncovered_questions(
        existing_questions=existing_questions,
        uncovered_questions=uncovered_questions,
        max_questions=MAX_UNCOVERED_TOPIC_PROMPTS,
    )
    if not selected_questions:
        return final_answer

    guided_answer = final_answer + "\n\nUncovered topics to confirm:\n" + "\n".join(
        [f"- {q}" for q in selected_questions]
    )
    persisted_questions = (existing_questions + selected_questions)[:MAX_OPEN_QUESTIONS_PERSISTED]
    try:
        await update_project_state(
            project_id,
            {"openQuestions": persisted_questions},
            db,
        )
    except Exception as prompt_update_error:  # noqa: BLE001
        logger.warning(f"Failed to persist openQuestions: {prompt_update_error}")

    return guided_answer


def _handle_failed_mcp_lookups(combined_updates: dict[str, Any], final_answer: str) -> str:
    """Surface failed MCP lookups to the user for clarification."""
    mcp_queries = combined_updates.get("mcpQueries")
    if not isinstance(mcp_queries, list):
        return final_answer

    failed_mcp_queries: list[str] = []
    for q in mcp_queries:
        if not isinstance(q, dict):
            continue
        result_urls = q.get("resultUrls")
        if isinstance(result_urls, list) and not result_urls:
            query_text = q.get("queryText")
            if isinstance(query_text, str) and query_text.strip():
                failed_mcp_queries.append(query_text.strip())

    if not failed_mcp_queries:
        return final_answer

    # Dedup and limit to 3
    deduped_failed = list(dict.fromkeys(failed_mcp_queries))

    guided_answer = final_answer + (
        "\n\nMCP lookups returned no results - "
        "please clarify the exact term/service to search for:\n"
    )
    for qt in deduped_failed[:3]:
        guided_answer += f"- '{qt}'\n"

    return guided_answer


def _extract_existing_questions(updated_state: dict[str, Any]) -> list[str]:
    open_questions = updated_state.get("openQuestions")
    if not isinstance(open_questions, list):
        return []
    return [q for q in open_questions if isinstance(q, str) and q.strip()]


def _normalize_question(question: str) -> str:
    return " ".join(question.lower().split())


def _select_new_uncovered_questions(
    *,
    existing_questions: list[str],
    uncovered_questions: list[str],
    max_questions: int,
) -> list[str]:
    existing_normalized = {_normalize_question(q) for q in existing_questions}

    selected: list[str] = []
    seen: set[str] = set()
    for question in uncovered_questions:
        if not isinstance(question, str) or not question.strip():
            continue
        normalized = _normalize_question(question)
        if normalized in existing_normalized or normalized in seen:
            continue
        seen.add(normalized)
        selected.append(question)
        if len(selected) >= max_questions:
            break

    return selected


def _handle_waf_followup_guardrail(
    *,
    next_stage: Any,
    combined_updates: dict[str, Any],
    updated_state: dict[str, Any],
    final_answer: str,
) -> str:
    stage = str(next_stage or "").strip().lower()
    if stage != "validate":
        return final_answer

    if _has_waf_update(combined_updates):
        return final_answer

    open_waf_items = _count_open_waf_items(updated_state)
    if open_waf_items <= 0:
        return final_answer

    guidance = (
        "\n\nWAF follow-up: validation is active and checklist evidence is still incomplete. "
        f"Please update at least one open WAF item status with explicit evidence (remaining open items: {open_waf_items})."
    )
    return final_answer + guidance


def _has_waf_update(combined_updates: dict[str, Any]) -> bool:
    waf_update = combined_updates.get("wafChecklist")
    if not isinstance(waf_update, dict):
        return False

    items = waf_update.get("items")
    if isinstance(items, list):
        return len(items) > 0
    if isinstance(items, dict):
        return len(items) > 0
    return False


def _count_open_waf_items(updated_state: dict[str, Any]) -> int:
    waf = updated_state.get("wafChecklist")
    if not isinstance(waf, dict):
        return 0

    items_raw = waf.get("items")
    items = items_raw.values() if isinstance(items_raw, dict) else items_raw
    if not isinstance(items, list):
        return 0

    remaining = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        evals = item.get("evaluations")
        latest = evals[-1] if isinstance(evals, list) and evals else None
        status = str((latest or {}).get("status", "notCovered")).lower()
        if status != "covered":
            remaining += 1
    return remaining

