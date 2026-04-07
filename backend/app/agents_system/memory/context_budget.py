"""Context budget service.

Manages token allocation across context pack sections to ensure
the assembled prompt fits within the model's context window.
"""

from __future__ import annotations


class ContextBudget:
    """Track token allocation across context sections."""

    def __init__(self, total_tokens: int = 12000) -> None:
        self._total = total_tokens
        self._used = 0
        self._sections: dict[str, int] = {}

    @property
    def total_tokens(self) -> int:
        return self._total

    @property
    def remaining_tokens(self) -> int:
        return max(0, self._total - self._used)

    def can_fit(self, tokens: int) -> bool:
        """Check if the given token count fits within remaining budget."""
        return tokens <= self.remaining_tokens

    def allocate(self, section_name: str, requested: int) -> int:
        """Allocate tokens to a section. Returns actual tokens allocated.

        If requested exceeds remaining, allocates whatever is left.
        """
        actual = min(requested, self.remaining_tokens)
        if actual > 0:
            self._sections[section_name] = self._sections.get(section_name, 0) + actual
            self._used += actual
        return actual

    def allocate_with_minimum(
        self, section_name: str, requested: int, minimum: int
    ) -> int:
        """Allocate tokens with a minimum guarantee.

        If remaining budget can't meet the minimum, gives whatever is left.
        Otherwise, allocates up to requested or remaining, whichever is less.
        """
        available = self.remaining_tokens
        if available <= 0:
            return 0
        actual = min(requested, available)
        # If we can't even meet minimum, give what's left
        if actual < minimum:
            actual = min(minimum, available)
        return self.allocate(section_name, actual)

    def usage_report(self) -> dict[str, object]:
        """Return a report of token budget usage."""
        return {
            "total_tokens": self._total,
            "used_tokens": self._used,
            "remaining_tokens": self.remaining_tokens,
            "sections": dict(self._sections),
        }
