"""Tiktoken-based token counting service.

Provides accurate token counting for GPT model families, used for
context budgeting, compaction threshold checks, and telemetry.
"""

from __future__ import annotations

import tiktoken


class TokenCounter:
    """Count tokens using tiktoken for a specific model."""

    def __init__(self, model_name: str = "gpt-4o") -> None:
        self._model_name = model_name
        try:
            self._encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to cl100k_base (GPT-4/4o family)
            self._encoding = tiktoken.get_encoding("cl100k_base")

    @property
    def model_name(self) -> str:
        return self._model_name

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string."""
        if not text:
            return 0
        return len(self._encoding.encode(text))

    def count_messages_tokens(self, messages: list[dict[str, str]]) -> int:
        """Count total tokens across a list of chat messages.

        Each message is expected to have 'role' and 'content' keys.
        Adds per-message overhead (~4 tokens) matching OpenAI's counting.
        """
        if not messages:
            return 0
        tokens_per_message = 4  # OpenAI overhead per message
        total = 0
        for msg in messages:
            total += tokens_per_message
            total += self.count_tokens(msg.get("role", ""))
            total += self.count_tokens(msg.get("content", ""))
        total += 2  # reply priming
        return total

    def fits_within_budget(self, text: str, budget: int) -> bool:
        """Check if text fits within a token budget."""
        return self.count_tokens(text) <= budget

    def truncate_to_budget(self, text: str, budget: int) -> str:
        """Truncate text to fit within a token budget.

        Decodes back from tokens to ensure valid truncation boundaries.
        """
        if budget <= 0:
            return ""
        tokens = self._encoding.encode(text)
        if len(tokens) <= budget:
            return text
        truncated_tokens = tokens[:budget]
        return self._encoding.decode(truncated_tokens)
