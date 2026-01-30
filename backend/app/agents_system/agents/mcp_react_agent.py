"""
MCP-specialized ReAct agent (extracted module).
Handles external tool discovery, execution, and result interpretation using LangChain ReAct pattern.

Phase 2: Allows optional injection of LLM, tools, and prompt to enable orchestration control.
Falls back to internal initialization when not provided to preserve behavior.
"""

import inspect
import logging
from collections.abc import Iterable
from typing import Any

from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI

from app.services.ai.ai_service import get_ai_service
from app.services.mcp.learn_mcp_client import MicrosoftLearnMCPClient

# build_tools previously used by older flow; tools are created via create_* helpers here
from ..config.react_prompts import REACT_TEMPLATE, SYSTEM_PROMPT
from ..langchain.agent_facade import AgentFacade
from ..langchain.prompt_builder import build_prompt_template
from ..tools.aaa_candidate_tool import create_aaa_tools
from ..tools.kb_tool import create_kb_tools
from ..tools.mcp_tool import create_mcp_tools

logger = logging.getLogger(__name__)


class MCPReActAgent:
    """
    ReAct agent specialized for Azure architecture assistance using MCP tools.

    Supports dependency injection for `llm`, `tools`, and `prompt` to enable orchestration-driven setup.
    If not provided, builds defaults internally (backward compatible).
    """

    def __init__(  # noqa: PLR0913
        self,
        openai_api_key: str | None = None,
        mcp_client: MicrosoftLearnMCPClient | None = None,
        model: str | None = None,
        temperature: float = 0.1,
        max_iterations: int = 8,
        max_execution_time: int = 60,
        verbose: bool = True,
        # Optional injected dependencies
        llm: ChatOpenAI | None = None,
        tools: list[BaseTool] | None = None,
        prompt: PromptTemplate | None = None,
    ):
        self.openai_api_key = openai_api_key
        self.mcp_client = mcp_client
        self.model = model
        self.temperature = temperature
        self.max_iterations = max_iterations
        self.max_execution_time = max_execution_time
        self.verbose = verbose

        # Injected or to be initialized
        self.llm: ChatOpenAI | None = llm
        self.tools: list[BaseTool] = tools or []
        self.prompt: PromptTemplate | None = prompt
        self.agent_facade: AgentFacade | None = None

        logger.info(
            f"MCPReActAgent initialized (model={model}, temperature={temperature}, injected_llm={'yes' if llm else 'no'})"
        )

    async def initialize(self, callbacks: Iterable[Any] | None = None) -> None:
        """Initialize the agent components asynchronously. Must be called before use."""
        self._initialize_llm()
        await self._initialize_tools()
        self._initialize_prompt()
        await self._initialize_facade(callbacks)
        logger.info("MCPReActAgent initialization complete")

    def _initialize_llm(self) -> None:
        """Construct the Chat LLM instance if not injected."""
        if self.llm is not None:
            return

        ai_service = get_ai_service()
        llm_kwargs = {}
        if self.model:
            llm_kwargs["model"] = self.model
        if self.temperature is not None:
            llm_kwargs["temperature"] = self.temperature
        self.llm = ai_service.create_chat_llm(**llm_kwargs)

    async def _initialize_tools(self) -> None:
        """Build the default toolset if not injected."""
        if self.tools:
            return

        if not self.mcp_client:
            raise ValueError("MCP client required to build tools")

        mcp_tools = await create_mcp_tools(self.mcp_client)
        kb_tools = create_kb_tools()
        aaa_tools = create_aaa_tools()
        self.tools = [*mcp_tools, *kb_tools, *aaa_tools]
        logger.info(f"Initialized {len(self.tools)} tools: {[t.name for t in self.tools]}")

    def _initialize_prompt(self) -> None:
        """Build the ReAct prompt template if not injected."""
        if self.prompt is not None:
            return

        tools_meta = [
            {"name": t.name, "description": getattr(t, "description", "")} for t in self.tools
        ]
        template_text = f"{SYSTEM_PROMPT}\n\n{REACT_TEMPLATE}"
        self.prompt = build_prompt_template(template_text, tools_meta)

    async def _initialize_facade(self, callbacks: Iterable[Any] | None) -> None:
        """Create and initialize the AgentFacade."""
        self.agent_facade = AgentFacade(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt,
            max_iterations=self.max_iterations,
            verbose=self.verbose,
        )

        init_fn = self.agent_facade.initialize
        maybe = None

        try:
            if callbacks is None:
                maybe = init_fn()
            else:
                try:
                    maybe = init_fn(callbacks=callbacks)
                except TypeError:
                    maybe = init_fn(callbacks)
        except TypeError:
            maybe = init_fn()

        if inspect.isawaitable(maybe):
            await maybe

    async def execute(self, user_query: str, project_context: str | None = None) -> dict:
        """Run the agent and return normalized result dictionary."""
        if not self.agent_facade:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        logger.info(f"Executing agent on query: {user_query}")
        agent_input = self._build_agent_input(user_query, project_context)

        try:
            result = await self.agent_facade.ainvoke(agent_input)
            return {
                "output": result.get("output", "No output generated"),
                "intermediate_steps": result.get("intermediate_steps", []),
                "success": True,
            }
        except Exception as e:  # noqa: BLE001
            return self._handle_execution_error(e)

    async def stream_execute(self, user_query: str, project_context: str | None = None):
        """Execute agent in streaming mode."""
        if not self.agent_facade:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        agent_input = self._build_agent_input(user_query, project_context)

        # Stream from the AgentFacade and normalize output chunks
        async for chunk in self.agent_facade.stream(agent_input):
            yield self._normalize_stream_chunk(chunk)

    def _build_agent_input(self, user_query: str, project_context: str | None) -> dict[str, str]:
        """Prepare inputs for agent, optionally embedding background context."""
        if not project_context:
            return {"input": user_query}

        contextualized_query = f"""CURRENT PROJECT CONTEXT:
{project_context}

---

User Question: {user_query}

IMPORTANT: The "CURRENT PROJECT CONTEXT" above is for your INTERNAL reference only. The user CANNOT see it.
In your Final Answer, you MUST explicitly include or summarize any requirements, architectural decisions, or facts from the context that are relevant to the user's question.
NEVER refer to the context as "detailed above" or "provided in the context" without repeating the details themselves.
"""
        return {"input": contextualized_query}

    def _handle_execution_error(self, e: Exception) -> dict[str, Any]:
        """Format error for API response with contextual tips."""
        err_text = str(e)
        hint = None
        if "max iterations" in err_text.lower():
            hint = "The agent reached its reasoning limit. Try asking a more specific question."
        elif "exceeded time" in err_text.lower() or "timeout" in err_text.lower():
            hint = "The agent timed out while reasoning. Consider narrowing the query."

        return {
            "output": f"I encountered an error while processing your query: {err_text}"
            + (f"\n\nTip: {hint}" if hint else ""),
            "intermediate_steps": [],
            "success": False,
            "error": err_text,
        }

    def _normalize_stream_chunk(self, chunk: Any) -> dict[str, Any]:
        """Normalize various LangChain stream chunk formats."""
        if isinstance(chunk, dict):
            return {
                "output": chunk.get("output"),
                "intermediate_steps": chunk.get("intermediate_steps", []),
                "success": True,
            }
        if isinstance(chunk, str):
            return {"output": chunk, "intermediate_steps": [], "success": True}

        return {"output": str(chunk), "intermediate_steps": [], "success": True}

