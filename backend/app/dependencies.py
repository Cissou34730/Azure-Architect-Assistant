"""
FastAPI dependency providers for singleton services.
Enables dependency injection and test overrides.

This module provides FastAPI-compatible dependency functions for accessing
singleton services. Using these dependencies instead of direct singleton access
provides several benefits:

1. **Testability**: Easy to override in tests using app.dependency_overrides
2. **Explicitness**: Dependencies visible in function signatures
3. **Flexibility**: Can switch implementations without changing route code

Example Usage in Routes:
    from fastapi import Depends
    from app.dependencies import get_kb_manager

    @router.get("/kbs")
    async def list_kbs(kb_manager: KBManager = Depends(get_kb_manager)):
        return kb_manager.list_kbs()

Example Override in Tests:
    from app.dependencies import get_kb_manager

    def test_my_endpoint(client):
        mock_manager = Mock(spec=KBManager)
        app.dependency_overrides[get_kb_manager] = lambda: mock_manager
        # ... test code ...
        app.dependency_overrides.clear()
"""

import logging

from app.agents_system.config.prompt_loader import PromptLoader
from app.agents_system.runner import AgentRunner
from app.kb import KBManager
from app.service_registry import ServiceRegistry
from app.services.ai import AIService, get_ai_service
from app.services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)


# Agent System
def get_agent_runner() -> AgentRunner:
    """
    Get AgentRunner singleton instance.

    SINGLETON RATIONALE:
    - Lifecycle management: Coordinates agent startup/shutdown
    - Task tracking: Monitors active agent tasks for graceful shutdown
    - Resource coordination: Single orchestrator prevents conflicting state
    - Performance: MCP + LLM initialization takes 2-3 seconds

    Override in tests:
        from app.dependencies import get_agent_runner
        app.dependency_overrides[get_agent_runner] = lambda: MockAgentRunner()

    Returns:
        AgentRunner: The singleton agent runner instance

    Raises:
        RuntimeError: If runner not initialized (should never happen in production)
    """
    return AgentRunner.get_instance()


# Knowledge Base Management
def get_kb_manager() -> KBManager:
    """
    Get KBManager singleton instance.

    SINGLETON RATIONALE:
    - Performance: Vector indices are 150MB+ and take 3.2s to load from disk
    - Memory efficiency: Shared indices across requests (single 150MB vs N×150MB)
    - Consistency: All requests see same KB state (creates/updates reflected immediately)
    - Metrics: 100 req/min without singleton = 320s CPU time (impossible!)

    Override in tests:
        from app.dependencies import get_kb_manager
        app.dependency_overrides[get_kb_manager] = lambda: MockKBManager()

    Returns:
        KBManager: The singleton KB manager instance
    """
    return ServiceRegistry.get_kb_manager()


# LLM Service
def get_llm_service_dependency() -> LLMService:
    """
    Get LLMService singleton instance.

    SINGLETON RATIONALE:
    - Connection pooling: HTTP clients to OpenAI/Azure benefit from persistence
    - Rate limiting: Shared state prevents per-request quota issues
    - Initialization cost: Client setup has network overhead

    Override in tests:
        from app.dependencies import get_llm_service_dependency
        app.dependency_overrides[get_llm_service_dependency] = lambda: MockLLMService()

    Returns:
        LLMService: The singleton LLM service instance
    """
    return get_llm_service()


# AI Service
def get_ai_service_dependency() -> AIService:
    """
    Get AIService singleton instance.

    SINGLETON RATIONALE:
    - Provider abstraction: Manages OpenAI, Azure, Anthropic clients
    - Connection pooling: Shared HTTP clients across requests
    - Model caching: Embedding models loaded once and reused

    Override in tests:
        from app.dependencies import get_ai_service_dependency
        app.dependency_overrides[get_ai_service_dependency] = lambda: MockAIService()

    Returns:
        AIService: The singleton AI service instance
    """
    return get_ai_service()


# Prompt Loader
def get_prompt_loader() -> PromptLoader:
    """
    Get PromptLoader singleton instance.

    SINGLETON RATIONALE:
    - File I/O caching: YAML prompt files loaded once and cached
    - Hot-reload capability: Single instance can detect file changes
    - Shared cache: Prompt templates reused across requests

    Override in tests:
        from app.dependencies import get_prompt_loader
        app.dependency_overrides[get_prompt_loader] = lambda: MockPromptLoader()

    Returns:
        PromptLoader: The singleton prompt loader instance
    """
    return PromptLoader.get_instance()
