"""Conversation compaction service.

Summarizes older conversation turns to stay within token budget,
preserving key decisions, requirements, and context.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents_system.config.prompt_loader import PromptLoader

from .token_counter import TokenCounter

logger = logging.getLogger(__name__)

_COMPACTION_PROMPT_FILE = "memory_compaction_prompt.yaml"


class CompactionService:
    """Manages conversation compaction (summarization of old turns)."""

    def __init__(
        self,
        compact_threshold_tokens: int = 4000,
        max_recent_turns: int = 10,
        model_name: str = "gpt-4o",
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        self._threshold = compact_threshold_tokens
        self._max_recent_turns = max_recent_turns
        self._counter = TokenCounter(model_name=model_name)
        self._prompt_loader = prompt_loader or PromptLoader.get_instance()

    def needs_compaction(self, messages: list[dict[str, str]]) -> bool:
        """Check if message history exceeds the compaction threshold."""
        if not messages:
            return False
        return self._counter.count_messages_tokens(messages) > self._threshold

    def split_messages_for_compaction(
        self, messages: list[dict[str, str]]
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        """Split messages into old (to summarize) and recent (to keep).

        Keeps the last `max_recent_turns` turn-pairs as recent.
        Returns (old_messages, recent_messages).
        """
        keep_count = self._max_recent_turns * 2
        if len(messages) <= keep_count:
            return [], messages
        split_idx = len(messages) - keep_count
        return messages[:split_idx], messages[split_idx:]

    def build_compaction_prompt(
        self,
        messages: list[dict[str, str]],
        existing_summary: str | None = None,
    ) -> str:
        """Build the prompt for the compaction LLM call."""
        compaction_prompt = self._load_compaction_prompt()
        rendered_turns = self._render_messages(messages)
        if existing_summary:
            template = str(compaction_prompt["with_existing_summary"])
            return template.format(
                existing_summary=existing_summary,
                new_turns=rendered_turns,
            )
        template = str(compaction_prompt["without_existing_summary"])
        return template.format(turns=rendered_turns)

    async def compact(
        self,
        messages: list[dict[str, str]],
        llm: Any,
        existing_summary: str | None = None,
    ) -> str | None:
        """Run compaction if needed. Returns summary or None if not needed.

        Args:
            messages: Full message history
            llm: LangChain-compatible LLM with ainvoke()
            existing_summary: Previous compaction summary to extend

        Returns:
            Summary string if compaction ran, None if not needed
        """
        if not self.needs_compaction(messages):
            return None

        old_messages, _recent = self.split_messages_for_compaction(messages)
        if not old_messages:
            return None

        prompt = self.build_compaction_prompt(old_messages, existing_summary)

        try:
            result = await llm.ainvoke(
                [
                    SystemMessage(content=self._load_system_prompt()),
                    HumanMessage(content=prompt),
                ]
            )
            summary = result.content if hasattr(result, "content") else str(result)
            logger.info(
                "Compaction produced summary of %d tokens from %d messages",
                self._counter.count_tokens(summary),
                len(old_messages),
            )
            return summary
        except Exception:
            logger.exception("Compaction LLM call failed")
            return existing_summary

    def clear_old_tool_results(
        self, messages: list[dict[str, str]], keep_recent: int = 2
    ) -> list[dict[str, str]]:
        """Remove tool result messages from old turns.

        Keeps tool results only in the last `keep_recent` turn-pairs.
        This prevents stale tool output from being replayed into context.
        """
        keep_count = keep_recent * 2
        if len(messages) <= keep_count:
            return messages

        boundary = len(messages) - keep_count
        result: list[dict[str, str]] = []
        for index, message in enumerate(messages):
            if index < boundary and message.get("role") == "tool":
                continue
            result.append(message)
        return result

    def _load_compaction_prompt(self) -> dict[str, str]:
        prompt = self._prompt_loader.load_prompt(_COMPACTION_PROMPT_FILE)
        compaction_prompt = prompt.get("compaction")
        if not isinstance(compaction_prompt, dict):
            raise ValueError("memory_compaction_prompt.yaml must define a 'compaction' mapping.")
        required_fields = ("system", "with_existing_summary", "without_existing_summary")
        missing = [field for field in required_fields if not isinstance(compaction_prompt.get(field), str)]
        if missing:
            missing_fields = ", ".join(missing)
            raise ValueError(
                "memory_compaction_prompt.yaml is missing required compaction fields: "
                f"{missing_fields}"
            )
        return {
            "system": str(compaction_prompt["system"]),
            "with_existing_summary": str(compaction_prompt["with_existing_summary"]),
            "without_existing_summary": str(compaction_prompt["without_existing_summary"]),
        }

    def _load_system_prompt(self) -> str:
        return self._load_compaction_prompt()["system"]

    def _render_messages(self, messages: list[dict[str, str]]) -> str:
        return "\n".join(
            f"[{message.get('role', 'unknown')}]: {message.get('content', '')}"
            for message in messages
        )
