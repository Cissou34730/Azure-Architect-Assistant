"""Compatibility wrapper for the feature-owned agent API service."""

from app.features.agent.application.agent_api_service import (
    AgentApiService,
    get_agent_api_service,
)

__all__ = ["AgentApiService", "get_agent_api_service"]

