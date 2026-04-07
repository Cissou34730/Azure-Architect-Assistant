"""Conversation compaction service.

Summarizes older conversation turns to stay within token budget,
preserving key decisions, requirements, and context.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from .token_counter import TokenCounter

logger = logging.getLogger(__name__)

_COMPACTION_SYSTEM_PROMPT = """\
You are a conversation summarizer for an Azure architecture assistant.
Summarize the conversation below into a concise summary that preserves:
- All architectural decisions made (accepted and rejected options)
- Requirements and constraints discovered
- Key technical recommendations
- Open questions and unresolved items
- Any specific Azure services discussed

Do NOT include:
- Greetings or small talk
- Redundant explanations
- Raw tool output details (just the conclusions)

Keep the summary factual, structured, and under 500 words."""


class CompactionService:
    """Manages conversation compaction (summarization of old turns)."""

    def __init__(
        self,
        compact_threshold_tokens: int = 4000,
        max_recent_turns: int = 10,
        model_name: str = "gpt-4o",
    ) -> None:
        self._threshold = compact_threshold_tokens
        self._max_recent_turns = max_recent_turns
        self._counter = TokenCounter(model_name=model_name)

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
        parts: list[str] = []
        if existing_summary:
            parts.append(f"Previous conversation summary:\n{existing_summary}\n")
        parts.append("New conversation turns to incorporate:\n")
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            parts.append(f"[{role}]: {content}\n")
        parts.append("\nProvide an updated, comprehensive summary.")
        return "\n".join(parts)

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
                    SystemMessage(content=_COMPACTION_SYSTEM_PROMPT),
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
