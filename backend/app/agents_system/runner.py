"""Agent system runner for shared runtime resources."""

import logging

from app.shared.ai.config import AIConfig
from app.shared.mcp.learn_mcp_client import MicrosoftLearnMCPClient

logger = logging.getLogger(__name__)


def _is_ai_runtime_configured() -> bool:
    """Return True when the selected AI provider configuration is valid."""
    try:
        AIConfig.default().validate_provider_config()
    except ValueError:
        return False
    return True


class AgentRunner:
    """Singleton holder for AI runtime readiness and MCP resources used by LangGraph nodes."""

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
        """Set or clear the global agent runner instance (for testing/lifecycle)."""
        cls._instance = instance

    def __init__(
        self,
        mcp_client: MicrosoftLearnMCPClient | None = None,
    ):
        """
        Initialize the agent runner.

        Args:
            mcp_client: MCP client instance
        """
        self.mcp_client = mcp_client

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

        if not _is_ai_runtime_configured():
            raise ValueError(
                "Configured AI provider is not ready (SecretKeeper or environment)"
            )

        logger.info("Agent system initialization complete")

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the agent system.
        """
        logger.info("Shutting down agent system...")

        logger.info("Agent system shutdown complete")

    def health_check(self) -> dict:
        """
        Check health status of the agent system.

        Returns:
            Dictionary with health status
        """
        ai_runtime_configured = _is_ai_runtime_configured()
        status = "healthy" if self.mcp_client and ai_runtime_configured else "not_initialized"
        health = {"status": status}
        health.update(
            {
                "mcp_client_connected": self.mcp_client is not None,
                "ai_runtime_configured": ai_runtime_configured,
                # Legacy response field name retained for API compatibility.
                "openai_configured": ai_runtime_configured,
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

