"""LangChain BaseChatModel backed by the GitHub Copilot SDK.

This wraps `CopilotRuntime.send_message()` / `stream_message()` so that
SDK-exclusive models (Claude, codex, GPT-5.x) can be used as a drop-in
replacement for `ChatOpenAI` in LangGraph agent pipelines.

Tool calling is supported via *prompt-based* injection: tool schemas are
appended to the system message and the model is instructed to emit
``<tool_call>`` XML blocks.  These blocks are parsed and returned as
standard LangChain ``AIMessage.tool_calls``, keeping full compatibility
with ``ToolNode`` and the LangGraph agent loop.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import AsyncIterator, Callable, Iterator, Sequence
from typing import Any, ClassVar

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool

from ..config import AIConfig
from .copilot_runtime import get_copilot_runtime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool-call prompt template
# ---------------------------------------------------------------------------

_TOOL_PREAMBLE = """
# Available Tools

You have FULL ACCESS to the following tools in this session.
They are available and ready to call — do NOT claim otherwise.
When you decide to use a tool, respond with a JSON object wrapped
in <tool_call> tags.  You may emit multiple <tool_call> blocks in
a single response.

Format:
<tool_call>
{"name": "<tool_name>", "arguments": {<arg_key>: <arg_value>, ...}}
</tool_call>

Do NOT wrap the JSON in markdown code fences.  Only use tools when they
are clearly needed to answer the user's request.

"""

_TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*(\{.*?\})\s*</tool_call>",
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# Public helpers (also used by tests)
# ---------------------------------------------------------------------------


def _format_messages_to_prompt(
    messages: list[BaseMessage],
) -> tuple[str | None, str]:
    """Convert LangChain messages to *(system, prompt)* pair for the SDK."""
    system_parts: list[str] = []
    prompt_parts: list[str] = []

    for msg in messages:
        if isinstance(msg, SystemMessage):
            system_parts.append(str(msg.content))
        elif isinstance(msg, HumanMessage):
            prompt_parts.append(f"USER: {msg.content}")
        elif isinstance(msg, AIMessage):
            if msg.tool_calls:
                calls_text = ", ".join(
                    f'{c["name"]}({json.dumps(c["args"])})'
                    for c in msg.tool_calls
                )
                prompt_parts.append(f"ASSISTANT: [tool calls: {calls_text}]")
            elif msg.content:
                prompt_parts.append(f"ASSISTANT: {msg.content}")
        elif isinstance(msg, ToolMessage):
            prompt_parts.append(
                f"TOOL RESULT ({msg.tool_call_id}): {msg.content}"
            )
        else:
            prompt_parts.append(f"{type(msg).__name__}: {msg.content}")

    system = "\n\n".join(system_parts) if system_parts else None
    prompt = "\n\n".join(prompt_parts)
    return system, prompt


def _parse_tool_calls(text: str) -> list[dict[str, Any]] | None:
    """Extract ``<tool_call>`` blocks from *text* and return LangChain tool-call dicts.

    Returns ``None`` when no valid tool calls are found.
    """
    matches = _TOOL_CALL_RE.findall(text)
    if not matches:
        return None

    calls: list[dict[str, Any]] = []
    for raw in matches:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        name = parsed.get("name")
        arguments = parsed.get("arguments", {})
        if not name:
            continue
        calls.append(
            {
                "id": f"call_{uuid.uuid4().hex[:24]}",
                "name": name,
                "args": arguments,
            }
        )

    return calls if calls else None


def _build_tool_system_section(tools: list[dict[str, Any]]) -> str:
    """Build the system-prompt section describing available tools."""
    lines = [_TOOL_PREAMBLE]
    for tool in tools:
        func = tool.get("function", tool)
        name = func.get("name", "unknown")
        desc = func.get("description", "")
        params = func.get("parameters", {})
        lines.append(f"## {name}")
        if desc:
            lines.append(desc)
        lines.append(f"Parameters: {json.dumps(params)}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CopilotChatModel
# ---------------------------------------------------------------------------


class CopilotChatModel(BaseChatModel):
    """LangChain chat model that delegates to the Copilot SDK for inference.

    This enables SDK-exclusive models (Claude, codex, GPT-5.x) to work with
    LangGraph agent pipelines including ``bind_tools()`` / ``ToolNode``.
    """

    model_name: str
    timeout: float = 120.0

    # Internal - set by the factory, not serialized.
    _config: AIConfig | None = None

    model_config: ClassVar[dict[str, bool]] = {"arbitrary_types_allowed": True}

    # -- Tool binding -------------------------------------------------------

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable:
        formatted = [convert_to_openai_tool(t) for t in tools]
        return self.bind(tools=formatted, **kwargs)

    # -- LangChain abstract interface ------------------------------------

    @property
    def _llm_type(self) -> str:  # type: ignore[override]
        return "copilot-sdk"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Sync fallback - delegates to the async path via a new event loop."""
        import asyncio  # noqa: PLC0415

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures  # noqa: PLC0415

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(
                    asyncio.run,
                    self._agenerate(messages, stop, run_manager=None, **kwargs),
                ).result()

        return asyncio.run(
            self._agenerate(messages, stop, run_manager=None, **kwargs)
        )

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        tools: list[dict[str, Any]] = kwargs.get("tools", [])
        system_msg, prompt = _format_messages_to_prompt(messages)

        # Inject tool schemas into the system message when tools are bound.
        if tools:
            tool_section = _build_tool_system_section(tools)
            system_msg = (
                f"{system_msg}\n\n{tool_section}" if system_msg else tool_section
            )

        runtime = await get_copilot_runtime(self._config or AIConfig.default())
        content = await runtime.send_message(
            prompt=prompt,
            model=self.model_name,
            system_message=system_msg,
            timeout=self.timeout,
        )

        # When tools are bound, look for <tool_call> blocks.
        if tools:
            parsed = _parse_tool_calls(content)
            if parsed:
                return ChatResult(
                    generations=[
                        ChatGeneration(
                            message=AIMessage(content="", tool_calls=parsed)
                        )
                    ]
                )

        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=content))]
        )

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        tools: list[dict[str, Any]] = kwargs.get("tools", [])
        system_msg, prompt = _format_messages_to_prompt(messages)

        # Inject tool schemas into the system message (mirrors _agenerate).
        if tools:
            tool_section = _build_tool_system_section(tools)
            system_msg = (
                f"{system_msg}\n\n{tool_section}" if system_msg else tool_section
            )

        runtime = await get_copilot_runtime(self._config or AIConfig.default())

        if tools:
            # When tools are bound we must accumulate the full response to
            # detect <tool_call> blocks before yielding.
            full_text: list[str] = []
            async for chunk in runtime.stream_message(
                prompt=prompt,
                model=self.model_name,
                system_message=system_msg,
                timeout=self.timeout,
            ):
                full_text.append(chunk)

            joined = "".join(full_text)
            parsed = _parse_tool_calls(joined)
            if parsed:
                yield ChatGenerationChunk(
                    message=AIMessageChunk(content="", tool_calls=parsed)
                )
            else:
                yield ChatGenerationChunk(
                    message=AIMessageChunk(content=joined)
                )
        else:
            async for chunk in runtime.stream_message(
                prompt=prompt,
                model=self.model_name,
                system_message=system_msg,
                timeout=self.timeout,
            ):
                yield ChatGenerationChunk(
                    message=AIMessageChunk(content=chunk)
                )

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        raise NotImplementedError(
            "Sync streaming not supported - use astream() instead."
        )
