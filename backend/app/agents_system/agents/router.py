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

from ...models.project import ConversationMessage
from ...projects_database import get_db
from ..langgraph.adapter import execute_chat, execute_project_chat
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

        result = await execute_chat(request.message)

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
    """Chat with the agent in the context of a specific architecture project."""
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

