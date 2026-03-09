"""Request and response DTOs for agent HTTP endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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
    reasoning_steps: list[AgentStep] = Field(default=[], description="Agent's reasoning steps")
    error: str | None = Field(default=None, description="Error message if failed")


class AgentHealthResponse(BaseModel):
    """Agent system health status."""

    status: str = Field(
        description="Health status: 'healthy', 'not_initialized', or 'unknown'"
    )
    mcp_client_connected: bool
    ai_runtime_configured: bool
    openai_configured: bool

