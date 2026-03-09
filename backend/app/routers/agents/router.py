"""Agent HTTP router (transport layer only)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.services.agent_api_service import (
    AgentApiService,
    get_agent_api_service,
)
from app.projects_database import get_db

from .models import (
    AgentChatRequest,
    AgentChatResponse,
    AgentHealthResponse,
    AgentStep,
    ProjectAgentChatRequest,
    ProjectAgentChatResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(
    request: AgentChatRequest,
    service: AgentApiService = Depends(get_agent_api_service),
) -> AgentChatResponse:
    """Chat with the Azure Architect Assistant agent."""
    try:
        payload = await service.chat(request.message)
        return AgentChatResponse(
            answer=str(payload.get("answer", "")),
            success=bool(payload.get("success", False)),
            reasoning_steps=[
                AgentStep(**step) for step in payload.get("reasoning_steps", [])
            ],
            error=payload.get("error"),
        )
    except RuntimeError as exc:
        logger.error("Agent not initialized: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent system not initialized. Please try again later.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Chat endpoint error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {exc!s}",
        ) from exc


@router.post("/projects/{project_id}/chat", response_model=ProjectAgentChatResponse)
async def chat_with_project_context(
    project_id: str,
    request: ProjectAgentChatRequest,
    db: AsyncSession = Depends(get_db),
    service: AgentApiService = Depends(get_agent_api_service),
) -> ProjectAgentChatResponse:
    """Chat with the agent in the context of a specific architecture project."""
    try:
        payload = await service.project_chat(project_id, request.message, db)
        return ProjectAgentChatResponse(
            answer=str(payload.get("answer", "")),
            success=bool(payload.get("success", False)),
            project_state=payload.get("project_state"),
            reasoning_steps=[
                AgentStep(**step) for step in payload.get("reasoning_steps", [])
            ],
            error=payload.get("error"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Project chat endpoint error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LangGraph execution failed: {exc!s}",
        ) from exc


@router.get("/projects/{project_id}/history")
async def get_conversation_history(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    service: AgentApiService = Depends(get_agent_api_service),
) -> dict[str, Any]:
    """Get conversation history for a project in chronological order."""
    try:
        return await service.get_project_history(project_id, db)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to load conversation history: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load conversation history: {exc!s}",
        ) from exc


@router.get("/health", response_model=AgentHealthResponse)
async def get_agent_health(
    service: AgentApiService = Depends(get_agent_api_service),
) -> AgentHealthResponse:
    """Check the health status of the agent system."""
    health = await service.health()
    return AgentHealthResponse(
        status=str(health.get("status", "unknown")),
        mcp_client_connected=bool(health.get("mcp_client_connected", False)),
        ai_runtime_configured=bool(health.get("ai_runtime_configured", False)),
        openai_configured=bool(health.get("openai_configured", False)),
    )


@router.get("/capabilities")
async def get_agent_capabilities(
    service: AgentApiService = Depends(get_agent_api_service),
) -> dict[str, Any]:
    """Get information about agent capabilities and available tools."""
    return service.capabilities()

