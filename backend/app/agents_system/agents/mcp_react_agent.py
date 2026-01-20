"""
MCP-specialized ReAct agent (extracted module).
Handles external tool discovery, execution, and result interpretation using LangChain ReAct pattern.

Phase 2: Allows optional injection of LLM, tools, and prompt to enable orchestration control.
Falls back to internal initialization when not provided to preserve behavior.
"""

import logging
from typing import Optional, List, Iterable, Any
import inspect
from langchain_openai import ChatOpenAI
from ...services.ai.ai_service import get_ai_service
from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool

from ..langchain.agent_facade import AgentFacade
from ..langchain.prompt_builder import build_prompt_template
# build_tools previously used by older flow; tools are created via create_* helpers here

from ..config.react_prompts import SYSTEM_PROMPT, REACT_TEMPLATE
from ..tools.mcp_tool import create_mcp_tools
from ..tools.kb_tool import create_kb_tools
from ..tools.aaa_candidate_tool import create_aaa_tools
from ...services.mcp.learn_mcp_client import MicrosoftLearnMCPClient

logger = logging.getLogger(__name__)


class MCPReActAgent:
    """
    ReAct agent specialized for Azure architecture assistance using MCP tools.

    Supports dependency injection for `llm`, `tools`, and `prompt` to enable orchestration-driven setup.
    If not provided, builds defaults internally (backward compatible).
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        mcp_client: Optional[MicrosoftLearnMCPClient] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_iterations: int = 8,
        max_execution_time: int = 60,
        verbose: bool = True,
        # Optional injected dependencies
        llm: Optional[ChatOpenAI] = None,
        tools: Optional[List[BaseTool]] = None,
        prompt: Optional[PromptTemplate] = None,
    ):
        self.openai_api_key = openai_api_key
        self.mcp_client = mcp_client
        self.model = model
        self.temperature = temperature
        self.max_iterations = max_iterations
        self.max_execution_time = max_execution_time
        self.verbose = verbose

        # Injected or to be initialized
        self.llm: Optional[ChatOpenAI] = llm
        self.tools: List[BaseTool] = tools or []
        self.prompt: Optional[PromptTemplate] = prompt
        self.agent_facade: Optional[AgentFacade] = None

        logger.info(
            f"MCPReActAgent initialized (model={model}, temperature={temperature}, injected_llm={'yes' if llm else 'no'})"
        )

    async def initialize(self, callbacks: Optional[Iterable[Any]] = None) -> None:
        """Initialize the agent components asynchronously. Must be called before use."""
        # Initialize LLM if not injected
        if self.llm is None:
            # Use centralized AIService to construct Chat LLM instances. This
            # allows provider/config centralization and easier testing.
            ai_service = get_ai_service()
            llm_kwargs = {}
            if self.model:
                llm_kwargs["model"] = self.model
            if self.temperature is not None:
                llm_kwargs["temperature"] = self.temperature
            # Let AIService use environment config for API keys if not provided
            self.llm = ai_service.create_chat_llm(**llm_kwargs)

        # Create tools if not injected
        if not self.tools:
            if not self.mcp_client:
                raise ValueError("MCP client required to build tools")
            mcp_tools = await create_mcp_tools(self.mcp_client)
            kb_tools = create_kb_tools()
            aaa_tools = create_aaa_tools()
            self.tools = [*mcp_tools, *kb_tools, *aaa_tools]
            logger.info(
                f"Initialized {len(self.tools)} tools: {[t.name for t in self.tools]}"
            )

        # Create prompt if not injected
        if self.prompt is None:
            # Build lightweight tools description dict for prompt builder
            tools_meta = [{"name": t.name, "description": getattr(t, "description", "")} for t in self.tools]
            self.prompt = build_prompt_template(f"{SYSTEM_PROMPT}\n\n{REACT_TEMPLATE}", tools_meta)

        # Custom parsing error handler to give LLM specific feedback
        def handle_parsing_error(error: Exception) -> str:
            error_msg = str(error)
            if "Missing 'Action:' after 'Thought:'" in error_msg:
                return (
                    "ERROR: You wrote 'Thought:' but did not follow it with 'Action:' or 'Final Answer:'. "
                    "You MUST write either:\n"
                    "Action: [tool_name]\nAction Input: [json]\n"
                    "OR\n"
                    "Final Answer: [your answer]\n"
                    "Please continue with the correct format."
                )
            return (
                f"Parsing error: {error_msg}. Please follow the exact format specified."
            )

        # Create AgentFacade to encapsulate future replacement with modern API
        self.agent_facade = AgentFacade(llm=self.llm, tools=self.tools, prompt=self.prompt, max_iterations=self.max_iterations, verbose=self.verbose)
        # AgentFacade.initialize may be an async coroutine or a test MagicMock.
        init_fn = getattr(self.agent_facade, "initialize")
        # Call initialize in a defensive way: some implementations accept a
        # `callbacks` keyword, others accept no args. When callbacks is None
        # call without args to avoid unexpected keyword errors.
        try:
            if callbacks is None:
                maybe = init_fn()
            else:
                try:
                    maybe = init_fn(callbacks=callbacks)
                except TypeError:
                    # Try positional fallback
                    maybe = init_fn(callbacks)
        except TypeError:
            # If the target is a MagicMock or similar that doesn't accept
            # the provided signature, call it without args and continue.
            maybe = init_fn()

        if inspect.isawaitable(maybe):
            await maybe

        logger.info("MCPReActAgent initialization complete")

    async def execute(
        self, user_query: str, project_context: Optional[str] = None
    ) -> dict:
        if not self.agent_facade:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        logger.info(f"Executing agent on query: {user_query}")
        agent_input = {"input": user_query}
        if project_context:
            contextualized_query = f"""CURRENT PROJECT CONTEXT:
{project_context}

---

User Question: {user_query}

IMPORTANT: The "CURRENT PROJECT CONTEXT" above is for your INTERNAL reference only. The user CANNOT see it. 
In your Final Answer, you MUST explicitly include or summarize any requirements, architectural decisions, or facts from the context that are relevant to the user's question. 
NEVER refer to the context as "detailed above" or "provided in the context" without repeating the details themselves.
"""
            agent_input["input"] = contextualized_query

        try:
            result = await self.agent_facade.ainvoke(agent_input)
            return {
                "output": result.get("output", "No output generated"),
                "intermediate_steps": result.get("intermediate_steps", []),
                "success": True,
            }
        except Exception as e:
            err_text = str(e)
            hint = None
            if "max iterations" in err_text.lower():
                hint = "The agent reached its reasoning limit. Try asking a more specific question or I can increase limits further if needed."
            elif "exceeded time" in err_text.lower() or "timeout" in err_text.lower():
                hint = "The agent timed out while reasoning. Consider narrowing the query or I can raise the time limit."
            return {
                "output": f"I encountered an error while processing your query: {err_text}"
                + (f"\n\nTip: {hint}" if hint else ""),
                "intermediate_steps": [],
                "success": False,
                "error": err_text,
            }

    async def stream_execute(
        self, user_query: str, project_context: Optional[str] = None
    ):
        if not self.agent_facade:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        agent_input = {"input": user_query}
        if project_context:
            contextualized_query = f"""CURRENT PROJECT CONTEXT:
{project_context}

---

User Question: {user_query}

IMPORTANT: The "CURRENT PROJECT CONTEXT" above is for your INTERNAL reference only. The user CANNOT see it. 
In your Final Answer, you MUST explicitly include or summarize any requirements, architectural decisions, or facts from the context that are relevant to the user's question. 
NEVER refer to the context as "detailed above" or "provided in the context" without repeating the details themselves.
"""
            agent_input["input"] = contextualized_query

        # Stream from the AgentFacade and normalize output chunks
        async for chunk in self.agent_facade.stream(agent_input):
            # chunk may be a dict-like result or a plain string or other shape
            if isinstance(chunk, dict):
                yield {
                    "output": chunk.get("output"),
                    "intermediate_steps": chunk.get("intermediate_steps", []),
                    "success": True,
                }
            elif isinstance(chunk, str):
                yield {"output": chunk, "intermediate_steps": [], "success": True}
            else:
                # Fallback: stringify unknown chunk
                yield {"output": str(chunk), "intermediate_steps": [], "success": True}
