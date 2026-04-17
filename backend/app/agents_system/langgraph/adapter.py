"""
Adapter for LangGraph project chat execution.

Provides a simple interface matching the router's expectations.
"""

import asyncio
import json
import logging
import re
import uuid
from collections.abc import AsyncIterator
from typing import Any, cast

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.contracts import (
    FinalStreamEventPayload,
    NextStepProposal,
    PendingChangeStreamEventPayload,
    StageClassification,
    StageStreamEventPayload,
    TextStreamEventPayload,
    ToolCallStreamEventPayload,
    ToolCallTrace,
    ToolResultStreamEventPayload,
    WorkflowCitation,
    WorkflowStageResult,
    normalize_structured_payload,
    serialize_sse_event,
)
from app.agents_system.tools.tool_registry import normalize_pending_change_tool_result
from app.shared.mcp.learn_mcp_client import MicrosoftLearnMCPClient

from ..runner import get_agent_runner
from ..services.response_sanitizer import sanitize_agent_output
from .graph_factory import build_project_chat_graph
from .nodes.agent_native import run_stage_aware_agent
from .state import GraphState

logger = logging.getLogger(__name__)
_INTERMEDIATE_STEP_PARTS = 2
_PREVIEW_LIMIT = 200
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


def _build_thread_config(thread_id: str | None) -> dict[str, Any] | None:
    """Build LangGraph config with thread_id for checkpointer."""
    if thread_id:
        return {"configurable": {"thread_id": thread_id}}
    return None


def _resolve_thread_id(thread_id: str | None) -> str:
    """Return the provided thread ID or mint one for checkpointer-backed runs."""
    if thread_id:
        return thread_id
    return str(uuid.uuid4())


def _build_reasoning_step(step: object) -> dict[str, str] | None:
    """Normalize an intermediate agent step for SSE consumers."""
    if not isinstance(step, tuple) or len(step) != _INTERMEDIATE_STEP_PARTS:
        return None

    action, observation = step
    return {
        "action": action.tool if hasattr(action, "tool") else str(action),
        "action_input": action.tool_input if hasattr(action, "tool_input") else "",
        "observation": str(observation)[:500],
    }


def _extract_urls(text: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for match in _URL_RE.findall(text or ""):
        normalized = match.rstrip(")].,;")
        if normalized in seen:
            continue
        seen.add(normalized)
        urls.append(normalized)
    return urls


def _preview_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=True, separators=(",", ":"))
        except TypeError:
            text = str(value)
    return text[:_PREVIEW_LIMIT]


def _build_tool_trace(step: object) -> ToolCallTrace | None:
    if not isinstance(step, tuple) or len(step) != _INTERMEDIATE_STEP_PARTS:
        return None

    action, observation = step
    tool_name = str(action.tool) if hasattr(action, "tool") else str(action)
    observation_text = str(observation)
    return ToolCallTrace(
        tool_name=tool_name,
        args_preview=_preview_text(action.tool_input if hasattr(action, "tool_input") else ""),
        result_preview=_preview_text(observation_text),
        citations=_extract_urls(observation_text),
        duration_ms=0,
    )


def _build_citations(tool_calls: list[ToolCallTrace]) -> list[WorkflowCitation]:
    citations: list[WorkflowCitation] = []
    seen_urls: set[str] = set()
    for tool_call in tool_calls:
        for url in tool_call.citations:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            citations.append(
                WorkflowCitation(
                    title=tool_call.tool_name,
                    url=url,
                    source=tool_call.tool_name,
                )
            )
    return citations


def _resolve_stage_name(result_state: dict[str, Any]) -> str:
    stage = result_state.get("next_stage")
    if isinstance(stage, str) and stage.strip():
        return stage.strip()
    return "general_chat"


def _resolve_stage_classification(result_state: dict[str, Any]) -> StageClassification | None:
    raw_classification = result_state.get("stage_classification")
    if raw_classification is None:
        return None
    return StageClassification.model_validate(raw_classification)


def _build_next_step(
    *,
    stage: str,
    pending_change_set: dict[str, Any] | None,
    structured_payload: dict[str, Any] | None,
    error: str | None,
) -> NextStepProposal:
    if error:
        return NextStepProposal(
            stage=stage,
            tool=None,
            rationale="Resolve the workflow error before continuing.",
            blocking_questions=[],
        )

    if isinstance(pending_change_set, dict):
        return NextStepProposal(
            stage="review_pending_changes",
            tool=None,
            rationale="Review and approve the pending change set before applying it.",
            blocking_questions=[],
        )

    if isinstance(structured_payload, dict):
        payload_type = structured_payload.get("type")
        if payload_type == "clarification_questions":
            questions = [
                str(question.get("text"))
                for question in structured_payload.get("questions", [])
                if isinstance(question, dict) and str(question.get("text") or "").strip()
            ]
            return NextStepProposal(
                stage="clarify",
                tool=None,
                rationale="The architect needs to answer the open clarification questions before planning can continue.",
                blocking_questions=questions,
            )
        if payload_type == "architect_choice":
            prompt = str(structured_payload.get("prompt") or "").strip()
            return NextStepProposal(
                stage=stage,
                tool=None,
                rationale="The architect needs to choose one of the proposed options before workflow state updates can continue.",
                blocking_questions=[prompt] if prompt else [],
            )

    return NextStepProposal(
        stage=stage,
        tool=None,
        rationale="Review the latest workflow result and continue when ready.",
        blocking_questions=[],
    )


def _build_workflow_result(
    *,
    result_state: dict[str, Any],
    summary: str,
) -> dict[str, Any]:
    tool_calls = [
        tool_call
        for step in result_state.get("intermediate_steps", [])
        if (tool_call := _build_tool_trace(step)) is not None
    ]
    structured_payload = normalize_structured_payload(result_state.get("structured_payload"))
    stage = _resolve_stage_name(result_state)
    stage_classification = _resolve_stage_classification(result_state)
    pending_change_set = _resolve_pending_change_set(result_state)
    workflow_result = WorkflowStageResult(
        stage=stage,
        stage_classification=stage_classification,
        summary=summary,
        pending_change_set=pending_change_set,
        citations=_build_citations(tool_calls),
        warnings=[],
        next_step=_build_next_step(
            stage=stage,
            pending_change_set=(
                pending_change_set.model_dump(mode="json", by_alias=True)
                if pending_change_set is not None
                else None
            ),
            structured_payload=structured_payload,
            error=result_state.get("error"),
        ),
        reasoning_summary=summary,
        tool_calls=tool_calls,
        structured_payload=structured_payload,
    )
    return workflow_result.model_dump(mode="json", by_alias=True)


def _resolve_pending_change_set(result_state: dict[str, Any]) -> Any:
    raw_pending_change_set = result_state.get("pending_change_set")
    if isinstance(raw_pending_change_set, dict):
        return raw_pending_change_set

    for step in reversed(result_state.get("intermediate_steps", [])):
        if not isinstance(step, tuple) or len(step) != _INTERMEDIATE_STEP_PARTS:
            continue
        _, observation = step
        canonical_result = normalize_pending_change_tool_result(observation)
        if canonical_result is not None:
            return canonical_result.pending_change_set
    return None


async def execute_chat(user_message: str) -> dict[str, Any]:
    """Execute a non-project chat using the LangGraph-native tool loop."""
    try:
        runner = await get_agent_runner()

        state: GraphState = {
            "user_message": user_message,
            "success": False,
            "retry_count": 0,
        }

        result = await run_stage_aware_agent(
            state,
            mcp_client=cast(MicrosoftLearnMCPClient, getattr(runner, "mcp_client", None)),
            openai_settings=getattr(runner, "openai_settings", None),
        )
        output = sanitize_agent_output(str(result.get("agent_output", "")))

        return {
            "output": output,
            "success": bool(result.get("success", False)),
            "intermediate_steps": result.get("intermediate_steps", []),
            "error": result.get("error"),
        }
    except Exception as e:
        logger.error("LangGraph chat execution failed: %s", e, exc_info=True)
        return {
            "output": "",
            "success": False,
            "intermediate_steps": [],
            "error": f"LangGraph chat execution failed: {e!s}",
        }


async def execute_project_chat(
    project_id: str,
    user_message: str,
    db: AsyncSession,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Execute project-aware chat via LangGraph, compatible with router expectations."""
    effective_thread_id = _resolve_thread_id(thread_id)
    try:
        response_message_id = str(uuid.uuid4())
        async with build_project_chat_graph(
            db,
            response_message_id,
        ) as graph:
            initial_state: GraphState = {
                "project_id": project_id,
                "user_message": user_message,
                "thread_id": effective_thread_id,
                "success": False,
                "retry_count": 0,
            }
            config = _build_thread_config(effective_thread_id)
            result = await graph.ainvoke(initial_state, config=config)
        output = str(result.get("final_answer", ""))
        if not output:
            output = sanitize_agent_output(str(result.get("agent_output", "")))
        project_state = result.get("updated_project_state")
        workflow_result = _build_workflow_result(result_state=result, summary=output)
        return {
            "answer": output,
            "output": output,
            "success": bool(result.get("success", False)),
            "project_state": project_state,
            "updated_project_state": project_state,
            "intermediate_steps": result.get("intermediate_steps", []),
            "error": result.get("error"),
            "thread_id": effective_thread_id,
            "workflow_result": workflow_result,
        }
    except Exception as e:
        logger.error("LangGraph project chat execution failed: %s", e, exc_info=True)
        return {
            "answer": "",
            "output": "",
            "success": False,
            "project_state": None,
            "updated_project_state": None,
            "intermediate_steps": [],
            "error": f"LangGraph project chat execution failed: {e!s}",
            "thread_id": effective_thread_id,
        }


async def execute_project_chat_stream(
    project_id: str,
    user_message: str,
    db: AsyncSession,
    thread_id: str | None = None,
) -> AsyncIterator[str]:
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    effective_thread_id = _resolve_thread_id(thread_id)

    async def _emit(event_type: str, payload: BaseModel | dict[str, Any]) -> None:
        for stream_event, stream_payload in _expand_stream_events(event_type, payload):
            await queue.put(serialize_sse_event(stream_event, stream_payload))

    async def _run() -> None:
        try:
            response_message_id = str(uuid.uuid4())
            async with build_project_chat_graph(
                db,
                response_message_id,
            ) as graph:
                initial_state: GraphState = {
                    "project_id": project_id,
                    "user_message": user_message,
                    "thread_id": effective_thread_id,
                    "success": False,
                    "retry_count": 0,
                }
                config: dict[str, Any] = {
                    "configurable": {
                        "thread_id": effective_thread_id,
                        "event_callback": _emit,
                    }
                }
                result_state = await graph.ainvoke(initial_state, config=config)
            final_answer = str(result_state.get("final_answer", ""))
            success = bool(result_state.get("success", False))
            updated_state = result_state.get("updated_project_state")
            reasoning_steps = []
            intermediate_steps = result_state.get("intermediate_steps", [])
            for step in intermediate_steps:
                reasoning_step = _build_reasoning_step(step)
                if reasoning_step is not None:
                    reasoning_steps.append(reasoning_step)
            fallback_output = sanitize_agent_output(str(result_state.get("agent_output", "")))
            final_output = final_answer if final_answer else fallback_output
            workflow_result = _build_workflow_result(
                result_state=result_state,
                summary=final_output,
            )
            stage_classification = _resolve_stage_classification(result_state)
            await _emit(
                "stage",
                StageStreamEventPayload(
                    stage=(stage_classification.stage if stage_classification else _resolve_stage_name(result_state)),
                    confidence=(stage_classification.confidence if stage_classification else 1.0),
                ),
            )
            pending_change_event = _build_pending_change_event(workflow_result)
            if pending_change_event is not None:
                await _emit("pending_change", pending_change_event)
            await _emit(
                "final",
                FinalStreamEventPayload(
                    answer=final_output,
                    success=success,
                    project_state=updated_state,
                    reasoning_steps=reasoning_steps,
                    error=result_state.get("error"),
                    thread_id=effective_thread_id,
                    workflow_result=WorkflowStageResult.model_validate(workflow_result),
                ),
            )
        except Exception as exc:
            logger.error("LangGraph streaming execution failed: %s", exc, exc_info=True)
            await _emit("error", {"error": f"Graph execution failed: {exc!s}"})
        finally:
            await queue.put(None)

    task = asyncio.create_task(_run())
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    finally:
        await task


def _expand_stream_events(
    event_type: str,
    payload: BaseModel | dict[str, Any],
) -> list[tuple[str, BaseModel | dict[str, Any]]]:
    if isinstance(payload, BaseModel):
        payload_dict = payload.model_dump(mode="python", by_alias=False, exclude_none=True)
    else:
        payload_dict = payload

    if event_type == "token":
        text = str(payload_dict.get("text", ""))
        return [
            ("token", payload_dict),
            ("text", TextStreamEventPayload(delta=text)),
        ]

    if event_type == "tool_start":
        tool = str(payload_dict.get("tool", ""))
        return [
            ("tool_start", payload_dict),
            (
                "tool_call",
                ToolCallStreamEventPayload(
                    tool=tool,
                    args_preview=_preview_text(payload_dict.get("tool_input")),
                ),
            ),
        ]

    if event_type == "tool_result":
        content = str(payload_dict.get("content", ""))
        return [
            (
                "tool_result",
                ToolResultStreamEventPayload(
                    tool=str(payload_dict.get("tool", "")),
                    result_preview=_preview_text(content),
                    citations=_extract_urls(content),
                    tool_call_id=(
                        str(payload_dict.get("tool_call_id"))
                        if payload_dict.get("tool_call_id") is not None
                        else None
                    ),
                    content=content,
                    status=(
                        str(payload_dict.get("status"))
                        if payload_dict.get("status") is not None
                        else None
                    ),
                ),
            )
        ]

    return [(event_type, payload)]


def _build_pending_change_event(
    workflow_result: dict[str, Any],
) -> PendingChangeStreamEventPayload | None:
    pending_change_set = workflow_result.get("pendingChangeSet")
    if not isinstance(pending_change_set, dict):
        return None

    change_set_id = str(pending_change_set.get("id") or "").strip()
    if not change_set_id:
        return None

    patch_count = len(pending_change_set.get("artifactDrafts", [])) if isinstance(
        pending_change_set.get("artifactDrafts"), list
    ) else 0
    summary = str(
        pending_change_set.get("bundleSummary") or pending_change_set.get("summary") or "Pending change set ready."
    )
    return PendingChangeStreamEventPayload(
        changeSetId=change_set_id,
        summary=summary,
        patchCount=patch_count,
    )


