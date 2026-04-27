"""Dedicated stage worker for clarify runtime execution."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.contracts import (
    ClarificationQuestionPayloadItem,
    ClarificationQuestionsPayload,
)
from app.agents_system.services.project_context import read_project_state
from app.features.agent.application.clarification_planner_worker import (
    ClarificationPlannerWorker,
)
from app.features.agent.application.clarification_resolution_worker import (
    ClarificationResolutionWorker,
    create_clarification_resolution_worker,
)
from app.features.agent.contracts.clarification_planner import (
    ClarificationPlanningResultContract,
)

from ..state import GraphState

logger = logging.getLogger(__name__)
_NON_ALPHANUMERIC_RE = re.compile(r"[^a-z0-9]+")

StreamEventCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]


def _user_wants_to_proceed(user_message: str) -> bool:
    """Detect when the user explicitly wants to proceed with default assumptions.

    This is intentionally more specific than _should_resolve_clarifications so that
    we can route to the no-LLM defaults path rather than the answer-extraction path.
    """
    normalized = " ".join(user_message.strip().lower().split())
    proceed_phrases = [
        "proceed with defaults",
        "proceed with default",
        "proceed",
        "use defaults",
        "use default",
        "continue with assumptions",
        "continue with defaults",
    ]
    return any(phrase in normalized for phrase in proceed_phrases)


async def execute_clarification_planner_node(
    state: GraphState,
    db: AsyncSession | None = None,
    *,
    worker: ClarificationPlannerWorker | None = None,
    resolution_worker: ClarificationResolutionWorker | Any | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the clarify stage through the clarification planning worker."""
    if state.get("next_stage") != "clarify":
        return {}

    event_callback = (
        ((config or {}).get("configurable") or {}).get("event_callback")
        or state.get("event_callback")
    )

    project_state = _project_state_from_graph_state(state)
    user_message = str(state.get("user_message") or "")

    # Proceed-with-defaults path: user explicitly wants to skip questions and accept defaults.
    # Checked before the standard resolution path so that "proceed with defaults" does not go
    # through the LLM-based answer extractor.  Default assumptions are persisted as pending
    # change artifacts so they are reviewable before becoming canonical.
    if _user_wants_to_proceed(user_message) and _has_open_clarification_questions(project_state):
        if db is None:
            raise ValueError("Clarification resolution requires a database session")
        resolver = resolution_worker or create_clarification_resolution_worker()
        try:
            change_set = await resolver.proceed_with_defaults(
                project_id=str(state["project_id"]),
                project_state=project_state,
                db=db,
                source_message_id=state.get("user_message_id"),
            )
            updated_project_state = await read_project_state(str(state["project_id"]), db)
            final_answer = _format_clarification_resolution(change_set)
            await _emit_stage_message(event_callback, final_answer)
            return {
                "agent_output": final_answer,
                "final_answer": final_answer,
                "intermediate_steps": [],
                "updated_project_state": updated_project_state or project_state,
                "handled_by_stage_worker": True,
                "success": True,
            }
        except ValueError as exc:
            logger.warning("Proceed-with-defaults did not yield actionable updates: %s", exc)
            final_answer = (
                "I couldn't find default assumptions for the open questions. "
                "Please answer the questions directly so I can proceed."
            )
            await _emit_stage_message(event_callback, final_answer)
            return {
                "agent_output": final_answer,
                "final_answer": final_answer,
                "intermediate_steps": [],
                "updated_project_state": project_state,
                "handled_by_stage_worker": True,
                "success": True,
            }
        except Exception as exc:
            logger.error("proceed-with-defaults failed: %s", exc, exc_info=True)
            final_answer = f"ERROR: Proceed with defaults failed: {exc!s}"
            await _emit_stage_message(event_callback, final_answer)
            return {
                "agent_output": final_answer,
                "final_answer": final_answer,
                "intermediate_steps": [],
                "handled_by_stage_worker": True,
                "success": False,
                "error": f"Proceed with defaults failed: {exc!s}",
            }

    if _should_resolve_clarifications(user_message=user_message, project_state=project_state):
        if db is None:
            raise ValueError("Clarification resolution requires a database session")
        resolver = resolution_worker or create_clarification_resolution_worker()
        try:
            change_set = await resolver.resolve_and_record_pending_change(
                project_id=str(state["project_id"]),
                user_message=user_message,
                project_state=project_state,
                db=db,
                source_message_id=state.get("user_message_id"),
            )
            updated_project_state = await read_project_state(str(state["project_id"]), db)
            final_answer = _format_clarification_resolution(change_set)
            await _emit_stage_message(event_callback, final_answer)
            return {
                "agent_output": final_answer,
                "final_answer": final_answer,
                "intermediate_steps": [],
                "updated_project_state": updated_project_state or project_state,
                "handled_by_stage_worker": True,
                "success": True,
            }
        except ValueError as exc:
            logger.warning("Clarification resolution did not yield actionable updates: %s", exc)
            final_answer = (
                "I couldn't identify specific answers to the clarification questions in your message. "
                "Could you reply more directly to one of the questions above? "
                "For example, answer the identity or recovery question, and I'll capture it as a reviewable update."
            )
            await _emit_stage_message(event_callback, final_answer)
            return {
                "agent_output": final_answer,
                "final_answer": final_answer,
                "intermediate_steps": [],
                "updated_project_state": project_state,
                "handled_by_stage_worker": True,
                "success": True,
            }
        except Exception as exc:
            logger.error("clarify resolution worker failed: %s", exc, exc_info=True)
            final_answer = f"ERROR: Clarification resolution failed: {exc!s}"
            await _emit_stage_message(event_callback, final_answer)
            return {
                "agent_output": final_answer,
                "final_answer": final_answer,
                "intermediate_steps": [],
                "handled_by_stage_worker": True,
                "success": False,
                "error": f"Clarification resolution failed: {exc!s}",
            }

    planner_worker = worker or ClarificationPlannerWorker()
    try:
        plan = await planner_worker.plan_questions(
            user_message=user_message,
            current_state=project_state,
            mindmap_coverage=_mindmap_coverage_from_graph_state(state),
        )
        final_answer = _format_clarification_plan(plan)
        await _emit_stage_message(event_callback, final_answer)
        return {
            "agent_output": final_answer,
            "final_answer": final_answer,
            "intermediate_steps": [],
            "handled_by_stage_worker": True,
            "success": True,
            "structured_payload": _build_clarification_structured_payload(plan),
        }
    except ValueError as exc:
        final_answer = f"ERROR: {exc!s}"
        await _emit_stage_message(event_callback, final_answer)
        return {
            "agent_output": final_answer,
            "final_answer": final_answer,
            "intermediate_steps": [],
            "handled_by_stage_worker": True,
            "success": False,
            "error": str(exc),
        }
    except Exception as exc:
        logger.error("clarify stage worker failed: %s", exc, exc_info=True)
        final_answer = f"ERROR: Clarification planning failed: {exc!s}"
        await _emit_stage_message(event_callback, final_answer)
        return {
            "agent_output": final_answer,
            "final_answer": final_answer,
            "intermediate_steps": [],
            "handled_by_stage_worker": True,
            "success": False,
            "error": f"Clarification planning failed: {exc!s}",
        }


def _project_state_from_graph_state(state: GraphState) -> dict[str, Any]:
    project_state = state.get("current_project_state")
    if isinstance(project_state, dict):
        return project_state
    return {}


def _mindmap_coverage_from_graph_state(state: GraphState) -> dict[str, Any] | None:
    mindmap_coverage = state.get("mindmap_coverage")
    if isinstance(mindmap_coverage, dict):
        return mindmap_coverage
    return None


def _format_clarification_plan(plan: ClarificationPlanningResultContract) -> str:
    total_questions = sum(len(group.questions) for group in plan.question_groups)
    lines = [
        "Clarification planning complete. "
        f"I identified {total_questions} high-impact question(s) grouped by theme.",
        "",
    ]

    for group in plan.question_groups:
        lines.append(f"**{group.theme}**")
        for index, question in enumerate(group.questions, start=1):
            lines.append(f"{index}. [{question.architectural_impact}] {question.question}")
            lines.append(f"   Why it matters: {question.why_it_matters}")
            if question.affected_decision:
                lines.append(f"   Affects decision: {question.affected_decision}")
            if question.default_assumption:
                lines.append(f"   Default if not answered: {question.default_assumption}")
            if question.risk_if_wrong:
                lines.append(f"   Risk if wrong: {question.risk_if_wrong}")
        lines.append("")

    lines.append("Please answer the questions you can, and I will use them to refine the architecture.")
    return "\n".join(lines).strip()


def _build_clarification_structured_payload(
    plan: ClarificationPlanningResultContract,
) -> dict[str, Any]:
    questions: list[ClarificationQuestionPayloadItem] = []
    for group in plan.question_groups:
        theme_slug = _slugify_theme(group.theme)
        for index, question in enumerate(group.questions, start=1):
            questions.append(
                ClarificationQuestionPayloadItem(
                    id=f"{theme_slug}-{index}",
                    text=question.question,
                    theme=group.theme,
                    why_it_matters=question.why_it_matters,
                    architectural_impact=question.architectural_impact,
                    priority=question.priority,
                    related_requirement_ids=list(question.related_requirement_ids),
                    affected_decision=question.affected_decision,
                    default_assumption=question.default_assumption,
                    risk_if_wrong=question.risk_if_wrong,
                )
            )
    return ClarificationQuestionsPayload(questions=questions).model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )


def _slugify_theme(theme: str) -> str:
    normalized = _NON_ALPHANUMERIC_RE.sub("-", theme.strip().lower()).strip("-")
    return normalized or "clarification"


def _format_clarification_resolution(change_set: Any) -> str:
    resolution_patch = {}
    if hasattr(change_set, "proposed_patch"):
        proposed_patch = change_set.proposed_patch
        if isinstance(proposed_patch, dict):
            resolution_patch = proposed_patch.get("_clarificationResolution") or {}
    question_count = len(resolution_patch.get("clarificationQuestions") or [])
    requirement_count = len(resolution_patch.get("requirements") or [])
    assumption_count = len(resolution_patch.get("assumptions") or [])
    return (
        "Clarification resolution complete. "
        f"I created pending change set `{getattr(change_set, 'id', '')}` with "
        f"{question_count} answered clarification(s), {requirement_count} updated requirement(s), "
        f"and {assumption_count} assumption(s). Review and approve it before it becomes canonical."
    )


def _should_resolve_clarifications(
    *,
    user_message: str,
    project_state: dict[str, Any],
) -> bool:
    if not _has_open_clarification_questions(project_state):
        return False
    normalized_message = " ".join(user_message.strip().lower().split())
    if not normalized_message:
        return False
    planning_requests = {
        "continue",
        "next",
        "go ahead",
        "what else",
        "what else?",
        "repeat",
    }
    if normalized_message in planning_requests:
        return False
    if any(
        phrase in normalized_message
        for phrase in (
            "what do you need",
            "what else do you need",
            "which questions",
            "what questions",
            "clarification questions",
            "please clarify",
        )
    ):
        return False
    return True


def _has_open_clarification_questions(project_state: dict[str, Any]) -> bool:
    questions = project_state.get("clarificationQuestions")
    if not isinstance(questions, list):
        return False
    return any(
        isinstance(question, dict)
        and str(question.get("status") or "open").strip().lower() not in {"answered", "resolved", "closed"}
        and str(question.get("question") or "").strip()
        for question in questions
    )


async def _emit_stage_message(
    callback: StreamEventCallback | Any,
    text: str,
) -> None:
    if not callable(callback):
        return
    await _emit(callback, "message_start", {"role": "assistant"})
    await _emit(callback, "token", {"text": text})


async def _emit(
    callback: StreamEventCallback,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    result = callback(event_type, payload)
    if asyncio.iscoroutine(result):
        await result
