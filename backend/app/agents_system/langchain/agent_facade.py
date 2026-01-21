import asyncio
import logging
from collections.abc import Iterable
from typing import Any

from langchain.agents import (
    AgentExecutor,
    AgentType,
    create_react_agent,
    initialize_agent,
)
from langchain.tools import BaseTool, Tool

from .facade_utils import make_single_input_wrapper, normalize_agent_result

logger = logging.getLogger(__name__)


class AgentFacade:
    """
    Unified facade for LangChain agents.
    Handles initialization of different agent types and normalizes their input/output.
    """

    def __init__(
        self,
        llm: Any | None = None,
        tools: list[Any] | None = None,
        prompt: Any | None = None,
        max_iterations: int = 8,
        verbose: bool = True,
    ) -> None:
        self.llm = llm
        self.tools = tools or []
        self.prompt = prompt
        self.max_iterations = max_iterations
        self.verbose = verbose

        self._executor: AgentExecutor | Any | None = None

    async def initialize(self, callbacks: Iterable[Any] | None = None) -> None:
        """Initializes the agent. Prefers modern LangChain 0.1+ ReAct agent logic."""
        if self.llm is None:
            raise ValueError("LLM must be provided to AgentFacade")

        built_tools = self._build_tools()

        try:
            if self.prompt is None:
                # If no prompt provided, we can't use create_react_agent directly
                logger.warning(
                    "No prompt provided to AgentFacade, falling back to legacy initialize_agent"
                )
                self._executor = initialize_agent(
                    tools=built_tools,
                    llm=self.llm,
                    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                    verbose=self.verbose,
                    max_iterations=self.max_iterations,
                    handle_parsing_errors=True,
                )
            else:
                agent = create_react_agent(llm=self.llm, tools=built_tools, prompt=self.prompt)
                self._executor = AgentExecutor(
                    agent=agent,
                    tools=built_tools,
                    verbose=self.verbose,
                    max_iterations=self.max_iterations,
                    handle_parsing_errors=True,
                    callbacks=list(callbacks) if callbacks else None,
                )

            logger.info("AgentFacade initialized successfully")
        except Exception as e:
            logger.exception(f"Failed to initialize AgentFacade: {e}")
            raise

    def _build_tools(self) -> list[BaseTool]:
        """Ensures all tools are in a format LangChain can understand."""
        built: list[BaseTool] = []
        for t in self.tools:
            if isinstance(t, BaseTool):
                built.append(t)
                continue

            # Dict-based tool definition
            if isinstance(t, dict):
                tool_dict = self._process_tool_dict(t)
                if tool_dict:
                    built.append(tool_dict)
                continue

            # Generic object with name/run
            tool_obj = self._process_tool_object(t)
            if tool_obj:
                built.append(tool_obj)

        return built

    def _process_tool_dict(self, t: dict[str, Any]) -> Tool | None:
        """Convert a dictionary definition into a LangChain Tool."""
        name = t.get("name")
        func = t.get("func")
        async_func = t.get("async_func") or t.get("arun")

        if not name or not (func or async_func):
            return None

        sync_wrapped, async_wrapped = make_single_input_wrapper(
            name, func or async_func, async_func
        )
        return Tool(
            name=name,
            func=sync_wrapped,
            coroutine=async_wrapped,
            description=t.get("description", ""),
        )

    def _process_tool_object(self, t: Any) -> Tool | None:
        """Convert a generic object with run/arun methods into a LangChain Tool."""
        name = getattr(t, "name", None) or getattr(t, "__name__", None)
        func = self._get_tool_func(t)
        async_func = getattr(t, "arun", None) or getattr(t, "ainvoke", None)
        desc = getattr(t, "description", "")

        if not name or not (func or async_func):
            return None

        sync_wrapped, async_wrapped = make_single_input_wrapper(
            name, func or async_func, async_func
        )
        return Tool(name=name, func=sync_wrapped, coroutine=async_wrapped, description=desc)

    def _get_tool_func(self, t: Any) -> Any:
        """Heuristic to find the synchronous execution function for a tool."""
        if hasattr(t, "run"):
            return t.run
        if callable(t):
            return t
        return None

    async def ainvoke(self, agent_input: dict[str, Any]) -> dict[str, Any]:
        """Asynchronously invokes the agent and returns a normalized result."""
        if self._executor is None:
            raise RuntimeError("AgentFacade not initialized. Call initialize() first.")

        # Ensure 'input' key is present as many agents expect it
        if "input" not in agent_input and "query" in agent_input:
            agent_input["input"] = agent_input["query"]

        try:
            if hasattr(self._executor, "ainvoke"):
                raw_result = await self._executor.ainvoke(agent_input)
            elif hasattr(self._executor, "arun"):
                input_str = agent_input.get("input") or str(agent_input)
                raw_result = await self._executor.arun(input_str)
            else:
                raw_result = await asyncio.to_thread(self._executor.run, agent_input)

            return normalize_agent_result(raw_result)
        except Exception as e:
            logger.exception(f"Error during agent invocation: {e}")
            raise

    async def stream(self, agent_input: dict[str, Any]):
        """Streams chunks from the agent if supported, otherwise yields a single result."""
        if self._executor is None:
            raise RuntimeError("AgentFacade not initialized. Call initialize() first.")

        if hasattr(self._executor, "astream"):
            async for chunk in self._executor.astream(agent_input):
                yield chunk
        else:
            yield await self.ainvoke(agent_input)

