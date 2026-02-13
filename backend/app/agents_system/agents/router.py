"""
Agent router.
FastAPI router for agent chat endpoints and request handling.
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.app_settings import get_settings
from ...models.project import ConversationMessage
from ...projects_database import get_db
from ..langgraph.adapter import execute_chat, execute_project_chat
from ..runner import get_agent_runner
from ..services.iteration_logging import (
    build_iteration_event_update,
    derive_mcp_query_updates_from_steps,
    derive_uncovered_topic_questions,
)
from ..services.project_context import (
    get_project_context_summary,
    read_project_state,
    update_project_state,
)
from ..services.state_update_parser import extract_state_updates

logger = logging.getLogger(__name__)


_AAA_STATE_UPDATE_MARKER = "AAA_STATE_UPDATE"
_ARCHITECT_CHOICE_MARKER_RE = re.compile(r"architect\s+choice\s+required\s*:", re.IGNORECASE)


def _extract_architect_choice_required_section(text: str) -> str | None:
    if not text:
        return None

    match = _ARCHITECT_CHOICE_MARKER_RE.search(text)
    if not match:
        return None

    start = match.start()
    end = text.find(_AAA_STATE_UPDATE_MARKER, start)
    if end < 0:
        end = len(text)

    section = text[start:end].strip()
    if not section:
        return None

    # Avoid bloating ProjectState.openQuestions.
    return section[:1500]


def _merge_updates(
    base: dict[str, Any] | None, extra: dict[str, Any] | None
) -> dict[str, Any]:
    """Helper to merge two project context update dictionaries."""
    combined: dict[str, Any] = {}
    for src in [base or {}, extra or {}]:
        for key, value in src.items():
            if key not in combined:
                combined[key] = value
                continue
            if isinstance(combined[key], list) and isinstance(value, list):
                combined[key] = [*combined[key], *value]
            elif isinstance(combined[key], dict) and isinstance(value, dict):
                combined[key] = {**combined[key], **value}
    return combined


def _extract_failed_queries(mcp_queries: list[Any]) -> list[str]:
    """Extract and deduplicate query texts from failed MCP results."""
    failed_mcp_queries: list[str] = []
    for q in mcp_queries:
        if not isinstance(q, dict):
            continue
        result_urls = q.get("resultUrls")
        if isinstance(result_urls, list) and not result_urls:
            query_text = q.get("queryText")
            if isinstance(query_text, str) and query_text.strip():
                failed_mcp_queries.append(query_text.strip())

    # Return stable deduplicated list
    return list(dict.fromkeys(failed_mcp_queries))


def _format_failed_mcp_feedback(combined_updates: dict[str, Any]) -> str:
    """Formatter for failed/empty MCP lookups (T025)."""
    mcp_queries = combined_updates.get("mcpQueries", [])
    if not isinstance(mcp_queries, list):
        return ""

    deduped_failed = _extract_failed_queries(mcp_queries)
    if not deduped_failed:
        return ""

    feedback = "\n\nMCP lookups returned no results — please clarify the exact term/service to search for:\n"
    for qt in deduped_failed[:3]:
        feedback += f"- {qt}: what exact Azure service/feature name (or official doc topic) should I use?\n"
    return feedback


def _format_conflict_feedback(updated_state: dict[str, Any]) -> str:
    """Formatter for surface merge conflicts to enforce human confirmation."""
    conflicts = updated_state.get("conflicts", [])
    if not isinstance(conflicts, list) or not conflicts:
        return ""

    feedback = "\n\nConflicts detected (no overwrite applied). Please confirm which value is correct for each path:\n"
    for c in conflicts[:5]:
        if not isinstance(c, dict):
            continue
        feedback += f"- {c.get('path')}: kept existing value; incoming suggestion available\n"
    return feedback


# Create router
router = APIRouter(prefix="/api/agent", tags=["agent"])


# Request/Response models
class ChatMessage(BaseModel):
    """Single chat message."""

    role: str = Field(description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(description="Message content")


class AgentChatRequest(BaseModel):
    """Request for agent chat endpoint."""

    message: str = Field(description="User's question or requirement")
    conversation_history: list[ChatMessage] | None = Field(
        default=None,
        description="Optional conversation history for context (not yet implemented)",
    )


class AgentStep(BaseModel):
    """Single reasoning step from the agent."""

    action: str = Field(description="Tool or action taken")
    action_input: str = Field(description="Input to the action")
    observation: str = Field(description="Result from the action")


class AgentChatResponse(BaseModel):
    """Response from agent chat endpoint."""

    answer: str = Field(description="Agent's final answer")
    success: bool = Field(description="Whether execution was successful")
    reasoning_steps: list[AgentStep] = Field(
        default=[], description="Agent's reasoning steps (Thought/Action/Observation)"
    )
    error: str | None = Field(default=None, description="Error message if failed")


class ProjectAgentChatRequest(BaseModel):
    """Request for project-aware agent chat."""

    message: str = Field(description="User's question or requirement")


class ProjectAgentChatResponse(BaseModel):
    """Response from project-aware agent chat."""

    answer: str = Field(description="Agent's final answer")
    success: bool = Field(description="Whether execution was successful")
    project_state: dict[str, Any] | None = Field(
        default=None, description="Updated project state if modified"
    )
    reasoning_steps: list[AgentStep] = Field(
        default=[], description="Agent's reasoning steps"
    )
    error: str | None = Field(default=None, description="Error message if failed")


class AgentHealthResponse(BaseModel):
    """Agent system health status."""

    status: str = Field(
        description="Health status: 'healthy', 'not_initialized', or 'unknown'"
    )
    mcp_client_connected: bool
    openai_configured: bool


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(request: AgentChatRequest) -> AgentChatResponse:
    """
    Chat with the Azure Architect Assistant agent.
    """
    try:
        logger.info(f"Received chat request: {request.message[:100]}...")

        settings = get_settings()
        if getattr(settings, "aaa_agent_engine", "langchain") == "langgraph":
            result = await execute_chat(request.message)
        else:
            runner = await get_agent_runner()
            result = await runner.execute_query(request.message)

        # Format intermediate steps for response
        reasoning_steps = []
        for action, observation in result.get("intermediate_steps", []):
            reasoning_steps.append(
                AgentStep(
                    action=action.tool if hasattr(action, "tool") else str(action),
                    action_input=action.tool_input if hasattr(action, "tool_input") else "",
                    observation=str(observation)[:500],
                )
            )

        return AgentChatResponse(
            answer=result["output"],
            success=result["success"],
            reasoning_steps=reasoning_steps,
            error=result.get("error"),
        )
    except RuntimeError as e:
        logger.error(f"Agent not initialized: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent system not initialized. Please try again later.",
        ) from e
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {e!s}",
        ) from e


async def _handle_langgraph_route(
    project_id: str, message: str, db: AsyncSession
) -> ProjectAgentChatResponse:
    """New execution path using LangGraph."""
    logger.info(f"Project {project_id}: Using LangGraph execution path")
    try:
        result = await execute_project_chat(project_id, message, db)

        # Format reasoning steps for response
        reasoning_steps = []
        for step in result.get("reasoning_steps", []):
            if isinstance(step, dict):
                reasoning_steps.append(
                    AgentStep(
                        action=str(step.get("action", "")),
                        action_input=str(step.get("action_input", "")),
                        observation=str(step.get("observation", "")),
                    )
                )

        return ProjectAgentChatResponse(
            answer=result["answer"],
            success=result["success"],
            project_state=result.get("project_state"),
            reasoning_steps=reasoning_steps,
            error=result.get("error"),
        )
    except Exception as e:
        logger.error(f"LangGraph execution failed: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LangGraph execution failed: {e!s}",
        ) from e


@router.post("/projects/{project_id}/chat", response_model=ProjectAgentChatResponse)
async def chat_with_project_context(
    project_id: str,
    request: ProjectAgentChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ProjectAgentChatResponse:
    """
    Chat with the agent in the context of a specific architecture project.
    Routes to either LangGraph or Legacy execution path based on settings.
    """
    settings = get_settings()

    # LangGraph-only: legacy execution is intentionally disabled.
    if getattr(settings, "aaa_agent_engine", "langchain") != "langgraph":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Agent engine is not configured for LangGraph. Set AAA_AGENT_ENGINE=langgraph "
                "(or AAA_USE_LANGGRAPH=true)."
            ),
        )

    return await _handle_langgraph_route(project_id, request.message, db)


def _save_conversation(
    project_id: str, request_message: str, answer: str, db: AsyncSession
) -> ConversationMessage:
    """Helper to save messages to the database."""
    user_msg_id = str(uuid.uuid4())
    agent_msg_id = str(uuid.uuid4())
    db.add(
        ConversationMessage(
            id=user_msg_id,
            project_id=project_id,
            role="user",
            content=request_message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )
    agent_message = ConversationMessage(
        id=agent_msg_id,
        project_id=project_id,
        role="assistant",
        content=answer,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    db.add(agent_message)
    return agent_message


def _apply_heuristic_feedback(
    answer: str,
    architect_choice_required: str | None,
    updated_state: dict[str, Any],
    combined_updates: dict[str, Any],
) -> str:
    """Helper to append feedback strings to the answer."""
    if not architect_choice_required:
        uncovered = derive_uncovered_topic_questions(updated_state)
        if uncovered:
            answer += "\n\nUncovered topics to confirm:\n" + "\n".join(
                [f"- {q}" for q in uncovered]
            )
            # Note: we don't await here as this is a sync helper, caller handles persistence
    answer += _format_failed_mcp_feedback(combined_updates)
    answer += _format_conflict_feedback(updated_state)
    return answer


def _extract_reasoning_steps(intermediate_steps: list[Any]) -> list[AgentStep]:
    """Helper to convert intermediate steps to AgentStep models."""
    return [
        AgentStep(
            action=action.tool if hasattr(action, "tool") else str(action),
            action_input=action.tool_input if hasattr(action, "tool_input") else "",
            observation=str(observation)[:500],
        )
        for action, observation in intermediate_steps
    ]


class LegacyUpdateParams(BaseModel):
    """Container for legacy update parameters to satisfy PLR0913."""
    project_id: str
    user_message_text: str
    answer: str
    choice_req: str | None
    project_state: dict[str, Any]
    intermediate_steps: list[Any]
    agent_msg_id: str


async def _apply_legacy_updates(
    project_id: str,
    combined: dict[str, Any],
    answer: str,
    choice_req: str | None,
    db: AsyncSession,
) -> tuple[dict[str, Any], str]:
    """Apply project state updates and derive follow-up questions."""
    try:
        updated_state = await update_project_state(project_id, combined, db)

        # NEW: Sync to normalized DB if feature enabled
        try:
            from app.agents_system.checklists.service import get_checklist_service
            from app.core.app_settings import get_settings

            settings = get_settings()
            if settings.aaa_feature_waf_normalized:
                service = await get_checklist_service(db=db, settings=settings)
                sync_result = await service.sync_project(
                    project_id=project_id, project_state=updated_state
                )
                logger.info(
                    f"Synced project {project_id} to normalized DB: {sync_result}"
                )
        except Exception as e:
            logger.error(f"Failed to sync project {project_id} to normalized DB: {e}")

        answer = _apply_heuristic_feedback(answer, choice_req, updated_state, combined)
        if not choice_req:
            uncovered = derive_uncovered_topic_questions(updated_state)
            if uncovered:
                await update_project_state(project_id, {"openQuestions": uncovered}, db)
        return updated_state, answer
    except Exception as update_error:  # noqa: BLE001
        logger.error(f"Project {project_id}: State update failed: {update_error}")
        return {}, answer


async def _process_legacy_updates(
    params: LegacyUpdateParams,
    db: AsyncSession,
) -> tuple[dict[str, Any], str]:
    """Extracted update processing logic to reduce complexity."""
    derived = derive_mcp_query_updates_from_steps(
        intermediate_steps=params.intermediate_steps, user_message=params.user_message_text
    )
    state_upd = (
        extract_state_updates(params.answer, params.user_message_text, params.project_state)
        if not params.choice_req
        else None
    )
    combined = _merge_updates(state_upd, derived)

    if params.choice_req:
        q_list = cast(list[str], combined.setdefault("openQuestions", []))
        q_list.append(params.choice_req)

    # Event and Persistence
    mcp_ids = [
        str(q.get("id"))
        for q in combined.get("mcpQueries", [])
        if isinstance(q, dict) and q.get("id")
    ]
    kind = "challenge" if "validate" in params.user_message_text.lower() else "propose"
    iter_upd = build_iteration_event_update(
        kind=kind,
        text=params.answer.strip()[:800],
        mcp_query_ids=mcp_ids,
        architect_response_message_id=params.agent_msg_id,
    )
    combined = _merge_updates(combined, iter_upd)

    if not combined:
        return params.project_state, params.answer

    return await _apply_legacy_updates(
        params.project_id, combined, params.answer, params.choice_req, db
    )


async def _handle_legacy_route(
    project_id: str, user_message_text: str, db: AsyncSession
) -> ProjectAgentChatResponse:
    """Legacy execution path using LangChain ReAct agent."""
    logger.info(f"Project {project_id}: Using legacy execution path")
    try:
        # Load and Prepare Context
        project_state = await read_project_state(project_id, db)
        if not project_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project state not found for {project_id}.",
            )
        context_summary = await get_project_context_summary(project_id, db)

        # Execute Agent
        runner = await get_agent_runner()
        result = await runner.execute_query(
            user_message_text,
            project_context=context_summary,
            project_id=project_id,
            session=db
        )
        intermediate_steps = result.get("intermediate_steps", [])
        answer = str(result.get("output", ""))

        # Parse Choice requirement
        choice_req = _extract_architect_choice_required_section(answer)
        if choice_req:
            logger.warning("Project %s: Architect choice required detected.", project_id)

        # Save History
        agent_msg = _save_conversation(project_id, user_message_text, answer, db)

        # Process Updates
        params = LegacyUpdateParams(
            project_id=project_id,
            user_message_text=user_message_text,
            answer=answer,
            choice_req=choice_req,
            project_state=project_state,
            intermediate_steps=intermediate_steps,
            agent_msg_id=agent_msg.id,
        )
        updated_state, answer = await _process_legacy_updates(params, db)

        return ProjectAgentChatResponse(
            answer=answer,
            success=bool(result.get("success")),
            project_state=updated_state,
            reasoning_steps=_extract_reasoning_steps(intermediate_steps),
            error=result.get("error"),
        )
    except Exception as e:
        logger.error(f"Legacy chat failed: {e}", exc_info=True)
        if isinstance(e, (HTTPException, RuntimeError)):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat: {e!s}",
        ) from e


@router.get("/projects/{project_id}/history")
async def get_conversation_history(project_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get conversation history for a project.

    Returns all messages (user and assistant) in chronological order.
    """
    try:
        result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.project_id == project_id)
            .order_by(ConversationMessage.timestamp)
        )
        messages = result.scalars().all()

        return {"messages": [msg.to_dict() for msg in messages], "total": len(messages)}
    except Exception as e:
        logger.error(f"Failed to load conversation history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load conversation history: {e!s}",
        ) from e


@router.get("/health", response_model=AgentHealthResponse)
async def get_agent_health() -> AgentHealthResponse:
    """
    Check the health status of the agent system.

    Returns information about:
    - Overall agent status
    - MCP client connection
    - OpenAI configuration
    """
    try:
        runner = await get_agent_runner()
        health = runner.health_check()

        return AgentHealthResponse(
            status=health["status"],
            mcp_client_connected=health["mcp_client_connected"],
            openai_configured=health["openai_configured"],
        )
    except RuntimeError:
        return AgentHealthResponse(
            status="not_initialized",
            mcp_client_connected=False,
            openai_configured=False,
        )


@router.get("/capabilities")
async def get_agent_capabilities():
    """
    Get information about the agent's capabilities and available tools.

    Returns:
    - List of available tools
    - Tool descriptions
    - Agent capabilities
    """
    return {
        "agent_type": "ReAct (Reasoning + Acting)",
        "primary_function": "Azure Architecture Assistance",
        "tools": [
            {
                "name": "microsoft_docs_search",
                "description": "Search Microsoft/Azure documentation semantically",
                "use_cases": [
                    "Find best practices",
                    "Get architectural guidance",
                    "Discover Azure services",
                ],
            },
            {
                "name": "microsoft_docs_fetch",
                "description": "Fetch complete documentation pages as markdown",
                "use_cases": [
                    "Get detailed tutorials",
                    "Read full guides",
                    "Access comprehensive documentation",
                ],
            },
            {
                "name": "microsoft_code_samples_search",
                "description": "Find official Microsoft code examples",
                "use_cases": [
                    "Get implementation examples",
                    "Find SDK usage",
                    "See code patterns",
                ],
            },
        ],
        "specializations": [
            "Azure Well-Architected Framework",
            "Security best practices",
            "Cost optimization",
            "Reliability patterns",
            "Performance optimization",
        ],
        "limitations": [
            "Only provides guidance from official Microsoft documentation",
            "Cannot execute code or make changes to Azure resources",
            "Requires internet connectivity for documentation access",
        ],
    }

