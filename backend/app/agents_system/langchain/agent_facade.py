import logging
from typing import Any, Dict, Iterable, List, Optional
import inspect

from .facade_utils import make_single_input_wrapper, normalize_agent_result

logger = logging.getLogger(__name__)


class AgentFacade:
    """
    Unified facade for LangChain agents.
    Handles initialization of different agent types and normalizes their input/output.
    """

    def __init__(
        self,
        llm: Optional[Any] = None,
        tools: Optional[List[Any]] = None,
        prompt: Optional[Any] = None,
        max_iterations: int = 8,
        verbose: bool = True,
    ) -> None:
        self.llm = llm
        self.tools = tools or []
        self.prompt = prompt
        self.max_iterations = max_iterations
        self.verbose = verbose

        self._agent: Optional[Any] = None
        self._executor: Optional[Any] = None

    async def initialize(self, callbacks: Optional[Iterable[Any]] = None) -> None:
        """
        Initializes the agent. Prefers modern LangChain 0.1+ ReAct agent logic.
        """
        if self.llm is None:
            raise ValueError("LLM must be provided to AgentFacade")

        built_tools = self._build_tools()

        try:
            from langchain.agents import AgentExecutor, create_react_agent
            
            if self.prompt is None:
                # If no prompt provided, we can't use create_react_agent directly
                # Fallback to older initialize_agent if possible or raise error
                logger.warning("No prompt provided to AgentFacade, falling back to legacy initialize_agent")
                from langchain.agents import initialize_agent, AgentType
                self._executor = initialize_agent(
                    tools=built_tools,
                    llm=self.llm,
                    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                    verbose=self.verbose,
                    max_iterations=self.max_iterations,
                    handle_parsing_errors=True
                )
            else:
                agent = create_react_agent(llm=self.llm, tools=built_tools, prompt=self.prompt)
                self._executor = AgentExecutor(
                    agent=agent,
                    tools=built_tools,
                    verbose=self.verbose,
                    max_iterations=self.max_iterations,
                    handle_parsing_errors=True,
                    callbacks=list(callbacks) if callbacks else None
                )
            
            logger.info("AgentFacade initialized successfully")
        except Exception as e:
            logger.exception(f"Failed to initialize AgentFacade: {e}")
            raise

    def _build_tools(self) -> List[Any]:
        """
        Ensures all tools are in a format LangChain can understand.
        """
        try:
            from langchain.tools import Tool, BaseTool
        except ImportError:
            Tool = None
            BaseTool = None

        built: List[Any] = []
        for t in self.tools:
            # If already a real LangChain BaseTool instance, keep it
            if BaseTool and isinstance(t, BaseTool):
                built.append(t)
                continue

            # If it's a dict with name and func
            if isinstance(t, dict) and "name" in t and ("func" in t or "async_func" in t):
                name = t["name"]
                func = t.get("func")
                async_func = t.get("async_func") or t.get("arun")
                sync_wrapped, async_wrapped = make_single_input_wrapper(name, func or async_func, async_func)
                if Tool:
                    built.append(Tool(
                        name=name, 
                        func=sync_wrapped, 
                        coroutine=async_wrapped,
                        description=t.get("description", "")
                    ))
                else:
                    built.append({"name": name, "func": async_wrapped, "description": t.get("description", "")})
                continue

            # Generic fallback for object with name and run/func/__call__
            name = getattr(t, "name", None) or getattr(t, "__name__", None)
            func = getattr(t, "run", None) or getattr(t, "func", None) or getattr(t, "__call__", None)
            async_func = getattr(t, "arun", None) or getattr(t, "ainvoke", None)
            desc = getattr(t, "description", "")
            
            if name and (func or async_func):
                sync_wrapped, async_wrapped = make_single_input_wrapper(name, func or async_func, async_func)
                if Tool:
                    built.append(Tool(
                        name=name, 
                        func=sync_wrapped, 
                        coroutine=async_wrapped,
                        description=desc
                    ))
                else:
                    built.append({"name": name, "func": async_wrapped, "description": desc})
        
        return built

    async def ainvoke(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asynchronously invokes the agent and returns a normalized result.
        """
        # Supports both _executor (LangChain AgentExecutor) and _agent (legacy/mock)
        target = self._executor or self._agent
        if target is None:
            raise RuntimeError("AgentFacade not initialized. Call initialize() first.")

        # Ensure 'input' key is present as many agents expect it
        if "input" not in agent_input and "query" in agent_input:
            agent_input["input"] = agent_input["query"]

        try:
            # AgentExecutor in LangChain 0.1+ has ainvoke
            if hasattr(target, "ainvoke"):
                raw_result = await target.ainvoke(agent_input)
            elif hasattr(target, "arun"):
                # Older versions or specific wrappers
                input_str = agent_input.get("input") or str(agent_input)
                raw_result = await target.arun(input_str)
            else:
                # Fallback to sync run in a thread if no async method found
                import asyncio
                raw_result = await asyncio.to_thread(target.run, agent_input)
            
            return normalize_agent_result(raw_result)
        except Exception as e:
            logger.exception(f"Error during agent invocation: {e}")
            raise

    async def stream(self, agent_input: Dict[str, Any]):
        """
        Streams chunks from the agent if supported, otherwise yields a single result.
        """
        target = self._executor or self._agent
        if target is None:
            raise RuntimeError("AgentFacade not initialized. Call initialize() first.")

        if hasattr(target, "astream"):
            async for chunk in target.astream(agent_input):
                yield chunk
        else:
            # Fallback for non-streaming executors
            yield await self.ainvoke(agent_input)
