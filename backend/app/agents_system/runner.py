"""
Agent system runner.
Entry point for initializing and running the agent system.
Delegates composition to AgentOrchestrator to keep runner thin.
"""

import logging
from typing import Any

from config.settings import OpenAISettings

from ..services.mcp.learn_mcp_client import MicrosoftLearnMCPClient
from .orchestrator.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)


class AgentRunner:
    """
    Runner for the Azure Architect Assistant agent system.
    """

    _instance: "AgentRunner | None" = None

    @classmethod
    def get_instance(cls) -> "AgentRunner":
        """Get the global agent runner instance."""
        if cls._instance is None:
            raise RuntimeError(
                "Agent runner not initialized. "
                "Ensure it's initialized in FastAPI startup event."
            )
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "AgentRunner | None") -> None:
        """Set or clear the global agent runner instance."""
        cls._instance = instance

    def __init__(
        self,
        openai_settings: OpenAISettings | None = None,
        mcp_client: MicrosoftLearnMCPClient | None = None,
    ):
        """
        Initialize the agent runner.

        Args:
            openai_settings: OpenAI configuration (defaults to env-based settings)
            mcp_client: MCP client instance (must be provided or initialized separately)
        """
        self.openai_settings = openai_settings or OpenAISettings()
        self.mcp_client = mcp_client
        self.orchestrator: AgentOrchestrator | None = None

        logger.info("AgentRunner initialized")

    async def initialize(self) -> None:
        """
        Initialize the agent system components.

        Raises:
            ValueError: If MCP client not provided
            RuntimeError: If initialization fails
        """
        if not self.mcp_client:
            raise ValueError("MCP client must be provided to AgentRunner")

        if not self.openai_settings.api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")

        logger.info("Initializing AgentOrchestrator...")

        # Create and initialize orchestrator (inject OpenAI settings)
        self.orchestrator = AgentOrchestrator(
            openai_settings=self.openai_settings,
            max_iterations=10,
            max_execution_time=60,
            verbose=True,
        )
        await self.orchestrator.initialize(self.mcp_client)

        logger.info("Agent system initialization complete")

    async def execute_query(
        self, 
        user_query: str, 
        project_context: str | None = None,
        project_id: str | None = None,
        session: Any = None
    ) -> dict:
        """
        Execute a user query through the agent.

        Args:
            user_query: User's architectural question or requirement
            project_context: Optional formatted project context string
            project_id: Optional project ID for WAF processing
            session: Optional DB session for WAF processing

        Returns:
            Dictionary with agent response and metadata
        """
        if not self.orchestrator:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        logger.info(f"Executing query: {user_query[:100]}...")

        result = await self.orchestrator.execute(
            user_query, project_context=project_context
        )

        # Process WAF updates if feature enabled and project_id/session provided
        from app.core.app_settings import get_settings
        settings = get_settings()
        if settings.aaa_feature_waf_normalized and project_id and session:
            try:
                from contextlib import asynccontextmanager
                from app.agents_system.checklists.engine import ChecklistEngine
                from app.agents_system.checklists.service import get_checklist_registry
                
                @asynccontextmanager
                async def session_factory():
                    yield session

                registry = get_checklist_registry(settings)
                engine = ChecklistEngine(
                    db_session_factory=session_factory, 
                    registry=registry, 
                    settings=settings
                )
                
                # engine.process_agent_result handles extraction from result dict
                await engine.process_agent_result(project_id, result)
            except Exception as e:
                logger.error(f"Failed to process WAF results for project {project_id}: {e}")

        logger.info(f"Query execution complete (success={result['success']})")

        return result

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the agent system.

        Cleanup resources, close connections, etc.
        """
        logger.info("Shutting down agent system...")

        # Orchestrator cleanup
        if self.orchestrator:
            await self.orchestrator.shutdown()
            self.orchestrator = None

        logger.info("Agent system shutdown complete")

    def health_check(self) -> dict:
        """
        Check health status of the agent system.

        Returns:
            Dictionary with health status
        """
        health = (
            self.orchestrator.health()
            if self.orchestrator
            else {"status": "not_initialized"}
        )
        health.update(
            {
                "mcp_client_connected": self.mcp_client is not None,
                "openai_configured": bool(self.openai_settings.api_key),
            }
        )
        return health


async def get_agent_runner() -> AgentRunner:
    """
    Get the global agent runner instance.

    Returns:
        Initialized AgentRunner instance

    Raises:
        RuntimeError: If runner not initialized
    """
    return AgentRunner.get_instance()


async def initialize_agent_runner(mcp_client: MicrosoftLearnMCPClient) -> None:
    """
    Initialize the global agent runner (called from FastAPI startup).

    Args:
        mcp_client: Initialized MCP client instance
    """
    logger.info("Initializing global agent runner...")

    runner = AgentRunner(mcp_client=mcp_client)
    await runner.initialize()
    AgentRunner.set_instance(runner)

    logger.info("Global agent runner initialized")


async def shutdown_agent_runner() -> None:
    """
    Shutdown the global agent runner (called from FastAPI shutdown).
    """
    try:
        runner = AgentRunner.get_instance()
        await runner.shutdown()
        AgentRunner.set_instance(None)
        logger.info("Global agent runner shutdown")
    except RuntimeError:
        pass

