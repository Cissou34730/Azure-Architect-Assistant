"""
Agent system runner.
Entry point for initializing and running the agent system.
Keeps initialization logic thin - delegates to agent for actual execution.
"""

import logging
from typing import Optional

from .agents.mcp_agent import MCPReActAgent
from ..services.mcp.learn_mcp_client import MicrosoftLearnMCPClient
from config.settings import OpenAISettings

logger = logging.getLogger(__name__)


class AgentRunner:
    """
    Runner for the Azure Architect Assistant agent system.
    
    Responsible for:
    - Configuration loading
    - Dependency injection (MCP client, OpenAI)
    - Agent initialization
    - Graceful lifecycle management
    """
    
    def __init__(
        self,
        openai_settings: Optional[OpenAISettings] = None,
        mcp_client: Optional[MicrosoftLearnMCPClient] = None,
    ):
        """
        Initialize the agent runner.
        
        Args:
            openai_settings: OpenAI configuration (defaults to env-based settings)
            mcp_client: MCP client instance (must be provided or initialized separately)
        """
        self.openai_settings = openai_settings or OpenAISettings()
        self.mcp_client = mcp_client
        self.agent: Optional[MCPReActAgent] = None
        
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
        
        logger.info("Initializing MCPReActAgent...")
        
        # Create agent
        self.agent = MCPReActAgent(
            openai_api_key=self.openai_settings.api_key,
            mcp_client=self.mcp_client,
            model=self.openai_settings.model,
            temperature=0.1,  # Low temperature for consistent architectural guidance
            max_iterations=10,
            verbose=True,
        )
        
        # Initialize agent components (async)
        await self.agent.initialize()
        
        logger.info("Agent system initialization complete")
    
    async def execute_query(self, user_query: str, project_context: Optional[str] = None) -> dict:
        """
        Execute a user query through the agent.
        
        Args:
            user_query: User's architectural question or requirement
            project_context: Optional formatted project context string
            
        Returns:
            Dictionary with agent response and metadata
            
        Raises:
            RuntimeError: If agent not initialized
        """
        if not self.agent:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        
        logger.info(f"Executing query: {user_query[:100]}...")
        
        result = await self.agent.execute(user_query, project_context=project_context)
        
        logger.info(f"Query execution complete (success={result['success']})")
        
        return result
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the agent system.
        
        Cleanup resources, close connections, etc.
        """
        logger.info("Shutting down agent system...")
        
        # Close MCP client if needed
        if self.mcp_client:
            # MCP client cleanup handled by lifecycle manager
            pass
        
        self.agent = None
        
        logger.info("Agent system shutdown complete")
    
    def health_check(self) -> dict:
        """
        Check health status of the agent system.
        
        Returns:
            Dictionary with health status
        """
        return {
            "status": "healthy" if self.agent else "not_initialized",
            "mcp_client_connected": self.mcp_client is not None,
            "openai_configured": bool(self.openai_settings.api_key),
        }


# Global runner instance (initialized by FastAPI lifecycle)
_agent_runner: Optional[AgentRunner] = None


async def get_agent_runner() -> AgentRunner:
    """
    Get the global agent runner instance.
    
    Returns:
        Initialized AgentRunner instance
        
    Raises:
        RuntimeError: If runner not initialized
    """
    global _agent_runner
    
    if _agent_runner is None:
        raise RuntimeError(
            "Agent runner not initialized. "
            "Ensure it's initialized in FastAPI startup event."
        )
    
    return _agent_runner


async def initialize_agent_runner(mcp_client: MicrosoftLearnMCPClient) -> None:
    """
    Initialize the global agent runner (called from FastAPI startup).
    
    Args:
        mcp_client: Initialized MCP client instance
    """
    global _agent_runner
    
    logger.info("Initializing global agent runner...")
    
    _agent_runner = AgentRunner(mcp_client=mcp_client)
    await _agent_runner.initialize()
    
    logger.info("Global agent runner initialized")


async def shutdown_agent_runner() -> None:
    """
    Shutdown the global agent runner (called from FastAPI shutdown).
    """
    global _agent_runner
    
    if _agent_runner:
        await _agent_runner.shutdown()
        _agent_runner = None
        
    logger.info("Global agent runner shutdown")
