"""
Agent Orchestrator.

Phase 3: Centralize tool and prompt assembly and inject them into the agent.
Keeps behavior stable while moving composition concerns out of the agent.
"""

import logging
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

from ..agents.mcp_react_agent import MCPReActAgent
from ..tools.mcp_tool import create_mcp_tools
from ..tools.kb_tool import create_kb_tools
from ..config.react_prompts import SYSTEM_PROMPT, REACT_TEMPLATE
from ..services.mcp.learn_mcp_client import MicrosoftLearnMCPClient
from config.settings import OpenAISettings

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Thin orchestrator that owns agent lifecycle and context injection.

    Phase 1 scope:
    - Keep behavior unchanged by delegating to existing MCPReActAgent
    - Centralize budgets (iterations/timeouts) and verbosity
    - Provide a single entrypoint: initialize/execute/shutdown
    """

    def __init__(
        self,
        openai_settings: Optional[OpenAISettings] = None,
        max_iterations: int = 10,
        max_execution_time: int = 60,
        verbose: bool = True,
    ) -> None:
        self.openai_settings = openai_settings or OpenAISettings()
        self.max_iterations = max_iterations
        self.max_execution_time = max_execution_time
        self.verbose = verbose

        self._mcp_client: Optional[MicrosoftLearnMCPClient] = None
        self._agent: Optional[MCPReActAgent] = None

    async def initialize(self, mcp_client: MicrosoftLearnMCPClient) -> None:
        """Initialize orchestrator and underlying agent with injected deps."""
        if not self.openai_settings.api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")

        logger.info("AgentOrchestrator: initializing with MCP client...")
        self._mcp_client = mcp_client

        # Assemble LLM
        llm = ChatOpenAI(
            model=self.openai_settings.model,
            temperature=0.1,
            openai_api_key=self.openai_settings.api_key,
        )

        # Assemble tools (MCP + KB)
        mcp_tools = await create_mcp_tools(mcp_client)
        kb_tools = create_kb_tools()
        tools = [*mcp_tools, *kb_tools]

        # Compose ReAct prompt with tool inventory
        prompt = PromptTemplate(
            template=f"{SYSTEM_PROMPT}\n\n{REACT_TEMPLATE}",
            input_variables=["input", "agent_scratchpad"],
            partial_variables={
                "tools": "\n".join([f"{tool.name}: {tool.description}" for tool in tools]),
                "tool_names": ", ".join([tool.name for tool in tools]),
            },
        )

        # Create agent with injected deps
        self._agent = MCPReActAgent(
            openai_api_key=self.openai_settings.api_key,
            mcp_client=mcp_client,
            model=self.openai_settings.model,
            temperature=0.1,
            max_iterations=self.max_iterations,
            max_execution_time=self.max_execution_time,
            verbose=self.verbose,
            llm=llm,
            tools=tools,
            prompt=prompt,
        )
        await self._agent.initialize()

        logger.info("AgentOrchestrator: initialized")

    async def execute(self, user_query: str, project_context: Optional[str] = None) -> dict:
        """Execute a query via the agent with optional context injection."""
        if not self._agent:
            raise RuntimeError("AgentOrchestrator not initialized")

        logger.info("AgentOrchestrator: executing query...")
        result = await self._agent.execute(user_query, project_context=project_context)
        logger.info("AgentOrchestrator: execution complete")
        return result

    async def shutdown(self) -> None:
        """Shutdown orchestrator and release references."""
        logger.info("AgentOrchestrator: shutdown")
        self._agent = None
        self._mcp_client = None

    def health(self) -> dict:
        return {
            "status": "initialized" if self._agent else "not_initialized",
            "openai_configured": bool(self.openai_settings.api_key),
            "max_iterations": self.max_iterations,
            "max_execution_time": self.max_execution_time,
        }
