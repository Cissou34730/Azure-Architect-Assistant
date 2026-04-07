"""Service layer for agent API endpoints.

Keeps orchestration and persistence logic out of FastAPI router modules.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.langgraph.adapter import (
    execute_chat,
    execute_project_chat,
    execute_project_chat_stream,
)
from app.agents_system.runner import get_agent_runner
from app.models.project import ConversationMessage


class AgentApiService:
    """Application service used by HTTP transport handlers for agent endpoints."""

    async def chat(self, message: str) -> dict[str, Any]:
        """Execute plain (non-project) agent chat."""
        result = await execute_chat(message)
        reasoning_steps = self._reasoning_steps_from_intermediate(
            result.get("intermediate_steps", [])
        )
        return {
            "answer": result.get("output", ""),
            "success": bool(result.get("success", False)),
            "reasoning_steps": reasoning_steps,
            "error": result.get("error"),
        }

    async def project_chat(
        self, project_id: str, message: str, db: AsyncSession, *, thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute project-aware chat via LangGraph."""
        result = await execute_project_chat(project_id, message, db, thread_id=thread_id)
        return {
            "answer": result.get("answer", ""),
            "success": bool(result.get("success", False)),
            "project_state": result.get("project_state"),
            "reasoning_steps": self._reasoning_steps_from_dicts(
                result.get("reasoning_steps", [])
            ),
            "error": result.get("error"),
            "thread_id": result.get("thread_id"),
        }

    async def project_chat_stream(
        self, project_id: str, message: str, db: AsyncSession, *, thread_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Execute project-aware chat as an SSE stream."""
        async for chunk in execute_project_chat_stream(project_id, message, db, thread_id=thread_id):
            yield chunk

    async def get_project_history(
        self, project_id: str, db: AsyncSession
    ) -> dict[str, Any]:
        """Load conversation history for a project."""
        result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.project_id == project_id)
            .order_by(ConversationMessage.timestamp)
        )
        messages = result.scalars().all()
        return {"messages": [msg.to_dict() for msg in messages], "total": len(messages)}

    async def health(self) -> dict[str, Any]:
        """Return agent runtime health."""
        try:
            runner = await get_agent_runner()
            return runner.health_check()
        except RuntimeError:
            return {
                "status": "not_initialized",
                "mcp_client_connected": False,
                "ai_runtime_configured": False,
                "openai_configured": False,
            }

    def capabilities(self) -> dict[str, Any]:
        """Return static capabilities metadata for the agent."""
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

    def _reasoning_steps_from_intermediate(
        self, intermediate_steps: list[Any]
    ) -> list[dict[str, str]]:
        steps: list[dict[str, str]] = []
        for action, observation in intermediate_steps:
            steps.append(
                {
                    "action": action.tool if hasattr(action, "tool") else str(action),
                    "action_input": (
                        action.tool_input if hasattr(action, "tool_input") else ""
                    ),
                    "observation": str(observation)[:500],
                }
            )
        return steps

    def _reasoning_steps_from_dicts(self, reasoning_steps: list[Any]) -> list[dict[str, str]]:
        steps: list[dict[str, str]] = []
        for step in reasoning_steps:
            if not isinstance(step, dict):
                continue
            steps.append(
                {
                    "action": str(step.get("action", "")),
                    "action_input": str(step.get("action_input", "")),
                    "observation": str(step.get("observation", "")),
                }
            )
        return steps


_agent_api_service = AgentApiService()


def get_agent_api_service() -> AgentApiService:
    """Get shared agent API service instance."""
    return _agent_api_service
