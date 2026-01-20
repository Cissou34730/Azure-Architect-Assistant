"""
Agent router.
FastAPI router for agent chat endpoints and request handling.
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..runner import get_agent_runner
from ..services.project_context import (
    read_project_state,
    update_project_state,
    get_project_context_summary,
)
from ..services.state_update_parser import extract_state_updates
from ..services.iteration_logging import (
    derive_mcp_query_updates_from_steps,
    build_iteration_event_update,
    derive_uncovered_topic_questions,
)
from ...projects_database import get_db
from ...models.project import ConversationMessage

logger = logging.getLogger(__name__)


_AAA_STATE_UPDATE_MARKER = "AAA_STATE_UPDATE"
_ARCHITECT_CHOICE_MARKER_RE = re.compile(r"architect\s+choice\s+required\s*:", re.IGNORECASE)


def _extract_architect_choice_required_section(text: str) -> Optional[str]:
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
    conversation_history: Optional[List[ChatMessage]] = Field(
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
    reasoning_steps: List[AgentStep] = Field(
        default=[], description="Agent's reasoning steps (Thought/Action/Observation)"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")


class ProjectAgentChatRequest(BaseModel):
    """Request for project-aware agent chat."""

    message: str = Field(description="User's question or requirement")


class ProjectAgentChatResponse(BaseModel):
    """Response from project-aware agent chat."""

    answer: str = Field(description="Agent's final answer")
    success: bool = Field(description="Whether execution was successful")
    project_state: Optional[Dict[str, Any]] = Field(
        default=None, description="Updated project state if modified"
    )
    reasoning_steps: List[AgentStep] = Field(
        default=[], description="Agent's reasoning steps"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")


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

    The agent uses ReAct reasoning to:
    1. Understand your architectural question
    2. Search Microsoft documentation for authoritative guidance
    3. Fetch detailed documentation when needed
    4. Find code examples and best practices
    5. Synthesize a comprehensive answer

    Example request:
    ```json
    {
        "message": "How should I secure my Azure SQL Database?"
    }
    ```

    Returns the agent's answer along with reasoning steps showing:
    - Which tools were called
    - What documentation was retrieved
    - How the answer was constructed
    """
    try:
        logger.info(f"Received chat request: {request.message[:100]}...")

        from ...core.config import get_settings

        settings = get_settings()
        if getattr(settings, "aaa_agent_engine", "langchain") == "langgraph":
            from ..langgraph.adapter import execute_chat

            result = await execute_chat(request.message)
        else:
            # Get the agent runner
            runner = await get_agent_runner()

            # Execute the query
            result = await runner.execute_query(request.message)

        # Format intermediate steps for response
        reasoning_steps = []
        for action, observation in result.get("intermediate_steps", []):
            reasoning_steps.append(
                AgentStep(
                    action=action.tool if hasattr(action, "tool") else str(action),
                    action_input=action.tool_input
                    if hasattr(action, "tool_input")
                    else "",
                    observation=str(observation)[:500],  # Truncate long observations
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
        )
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {str(e)}",
        )


@router.post("/projects/{project_id}/chat", response_model=ProjectAgentChatResponse)
async def chat_with_project_context(
    project_id: str,
    request: ProjectAgentChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ProjectAgentChatResponse:
    """
    Chat with the agent in the context of a specific architecture project.

    The agent will:
    1. Load the current project state (requirements, NFRs, architecture)
    2. Consider project context when answering questions
    3. Search Azure documentation for relevant guidance
    4. Detect if the answer updates project requirements
    5. Update the project state if needed

    Example request:
    ```json
    {
        "message": "We need 99.9% availability for our web app"
    }
    ```

    The agent will understand this is an NFR and may update the project state accordingly.
    """
    from ...core.config import get_settings
    from ..langgraph.adapter import execute_project_chat
    
    settings = get_settings()
    
    # Phase 3+: Engine routing
    if getattr(settings, "aaa_agent_engine", "langchain") == "langgraph":
        logger.info(f"Project {project_id}: Using LangGraph execution path")
        try:
            result = await execute_project_chat(project_id, request.message, db)
            
            # Format reasoning steps for response
            reasoning_steps = []
            for step in result.get("reasoning_steps", []):
                if isinstance(step, dict):
                    reasoning_steps.append(
                        AgentStep(
                            action=step.get("action", ""),
                            action_input=step.get("action_input", ""),
                            observation=step.get("observation", ""),
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"LangGraph execution failed: {str(e)}",
            )
    
    # Legacy execution path
    logger.info(f"Project {project_id}: Using legacy execution path")
    try:
        logger.info(f"Project {project_id}: Received agent chat request")

        # Load project context
        project_state = await read_project_state(project_id, db)
        if not project_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project state not found for {project_id}. Please analyze documents first.",
            )

        # Get formatted context summary
        context_summary = await get_project_context_summary(project_id, db)

        # Get the agent runner
        runner = await get_agent_runner()

        # Execute with project context
        result = await runner.execute_query(
            request.message, project_context=context_summary
        )

        intermediate_steps = result.get("intermediate_steps", [])
        logger.info(
            "Project %s: Agent execution finished (success=%s, steps=%d)",
            project_id,
            result.get("success"),
            len(intermediate_steps) if isinstance(intermediate_steps, list) else 0,
        )

        # Parse response for potential state updates
        updated_state = None
        answer = result["output"]

        architect_choice_required = _extract_architect_choice_required_section(answer)
        if architect_choice_required:
            logger.warning(
                "Project %s: Architect choice required detected; blocking state updates until explicit selection.",
                project_id,
            )

        # Save user message to database
        user_message = ConversationMessage(
            id=str(uuid.uuid4()),
            project_id=project_id,
            role="user",
            content=request.message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        db.add(user_message)

        # Save agent response to database
        agent_message = ConversationMessage(
            id=str(uuid.uuid4()),
            project_id=project_id,
            role="assistant",
            content=answer,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        db.add(agent_message)

        # Derive per-iteration MCP query logging from tool calls.
        derived_updates: Dict[str, Any] = derive_mcp_query_updates_from_steps(
            intermediate_steps=intermediate_steps,
            user_message=request.message,
        )
        mcp_queries_count = 0
        if isinstance(derived_updates, dict) and isinstance(derived_updates.get("mcpQueries"), list):
            mcp_queries_count = len(derived_updates.get("mcpQueries"))
        if mcp_queries_count:
            logger.info("Project %s: Derived MCP queries=%d", project_id, mcp_queries_count)

        # Look for state update suggestions in the answer.
        state_updates = extract_state_updates(answer, request.message, project_state)
        if architect_choice_required:
            # FR-018: if sources conflict, require an explicit architect choice before persisting a final selection.
            # We still persist derived MCP logs and iteration events.
            state_updates = None

        # Combine structured/heuristic updates with derived logging updates.
        combined_updates: Dict[str, Any] = {}
        for src in [state_updates or {}, derived_updates or {}]:
            for key, value in src.items():
                if key not in combined_updates:
                    combined_updates[key] = value
                    continue
                if isinstance(combined_updates[key], list) and isinstance(value, list):
                    combined_updates[key] = [*combined_updates[key], *value]
                elif isinstance(combined_updates[key], dict) and isinstance(value, dict):
                    combined_updates[key] = {**combined_updates[key], **value}

        if architect_choice_required:
            combined_updates.setdefault("openQuestions", [])
            if isinstance(combined_updates["openQuestions"], list):
                combined_updates["openQuestions"].append(architect_choice_required)

        # Add an iteration event (SC-010) with MCP citations.
        mcp_query_ids = [q.get("id") for q in combined_updates.get("mcpQueries", []) if isinstance(q, dict) and q.get("id")]
        kind = "challenge" if any(k in request.message.lower() for k in ["validate", "validation", "waf", "risk", "security benchmark"]) else "propose"
        event_text = answer.strip()[:800]
        iteration_update = build_iteration_event_update(
            kind=kind,
            text=event_text,
            mcp_query_ids=[str(qid) for qid in mcp_query_ids if qid],
            architect_response_message_id=agent_message.id,
        )
        for key, value in iteration_update.items():
            if key not in combined_updates:
                combined_updates[key] = value
            elif isinstance(combined_updates[key], list) and isinstance(value, list):
                combined_updates[key] = [*combined_updates[key], *value]

        if combined_updates:
            logger.info(
                "Project %s: Applying state updates (keys=%s)",
                project_id,
                ",".join(sorted([str(k) for k in combined_updates.keys()])),
            )
            try:
                updated_state = await update_project_state(project_id, combined_updates, db)

                # Heuristic uncovered-topic prompts (until full coverage tracking exists).
                if not architect_choice_required:
                    uncovered_questions = derive_uncovered_topic_questions(updated_state)
                    if uncovered_questions:
                        answer += "\n\nUncovered topics to confirm:\n" + "\n".join(
                            [f"- {q}" for q in uncovered_questions]
                        )
                        try:
                            await update_project_state(
                                project_id,
                                {"openQuestions": uncovered_questions},
                                db,
                            )
                        except Exception as prompt_update_error:
                            logger.warning(
                                f"Project {project_id}: Failed to persist openQuestions: {prompt_update_error}"
                            )

                # Record and surface failed/empty MCP lookups (T025).
                failed_mcp_queries: List[str] = []
                for q in combined_updates.get("mcpQueries", []) if isinstance(combined_updates.get("mcpQueries"), list) else []:
                    if not isinstance(q, dict):
                        continue
                    result_urls = q.get("resultUrls")
                    if isinstance(result_urls, list) and len(result_urls) == 0:
                        query_text = q.get("queryText")
                        if isinstance(query_text, str) and query_text.strip():
                            failed_mcp_queries.append(query_text.strip())

                if failed_mcp_queries:
                    deduped_failed: List[str] = []
                    seen_failed: set[str] = set()
                    for qt in failed_mcp_queries:
                        if qt not in seen_failed:
                            seen_failed.add(qt)
                            deduped_failed.append(qt)

                    answer += "\n\nMCP lookups returned no results — please clarify the exact term/service to search for:\n"
                    for qt in deduped_failed[:3]:
                        answer += f"- {qt}: what exact Azure service/feature name (or official doc topic) should I use?\n"

                    logger.warning(
                        "Project %s: MCP lookups returned no results (count=%d, sample=%s)",
                        project_id,
                        len(deduped_failed),
                        "; ".join(deduped_failed[:3]),
                    )

                # Surface merge conflicts in the answer to enforce human confirmation.
                conflicts = updated_state.get("conflicts") if isinstance(updated_state, dict) else None
                if isinstance(conflicts, list) and conflicts:
                    answer += "\n\nConflicts detected (no overwrite applied). Please confirm which value is correct for each path:\n"
                    for c in conflicts[:5]:
                        if not isinstance(c, dict):
                            continue
                        answer += f"- {c.get('path')}: kept existing value; incoming suggestion available\n"

                    conflict_paths = [
                        str(c.get("path"))
                        for c in conflicts
                        if isinstance(c, dict) and c.get("path")
                    ]
                    logger.warning(
                        "Project %s: Merge conflicts detected (count=%d, paths=%s)",
                        project_id,
                        len(conflicts),
                        ",".join(conflict_paths[:10]),
                    )

                logger.info(f"Project {project_id}: State updated successfully")
            except Exception as update_error:
                logger.error(
                    "Project %s: Failed to update state (%s)",
                    project_id,
                    update_error,
                    exc_info=True,
                )
                # Don't fail the request, just log the error

        # Format reasoning steps
        reasoning_steps = []
        for action, observation in intermediate_steps:
            reasoning_steps.append(
                AgentStep(
                    action=action.tool if hasattr(action, "tool") else str(action),
                    action_input=action.tool_input
                    if hasattr(action, "tool_input")
                    else "",
                    observation=str(observation)[:500],
                )
            )

        return ProjectAgentChatResponse(
            answer=answer,
            success=result["success"],
            project_state=updated_state,
            reasoning_steps=reasoning_steps,
            error=result.get("error"),
        )

    except HTTPException:
        raise
    except RuntimeError as e:
        logger.error(f"Agent not initialized: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent system not initialized. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Project chat endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {str(e)}",
        )


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
            detail=f"Failed to load conversation history: {str(e)}",
        )


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
