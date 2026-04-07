"""Context pack schema.

Defines the typed structure for stage-specific context packs assembled
before injecting into the agent prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContextSection:
    """A single section of the context pack."""

    name: str
    content: str
    token_count: int = 0
    priority: int = 1  # 1=highest, 5=lowest; low-priority dropped first


@dataclass
class ContextPack:
    """Complete context pack assembled for a single agent turn."""

    stage: str
    sections: list[ContextSection] = field(default_factory=list)
    budget_meta: dict[str, Any] = field(default_factory=dict)

    def to_prompt(self) -> str:
        """Assemble sections into the final prompt string."""
        parts: list[str] = []
        for section in self.sections:
            if section.content.strip():
                parts.append(section.content)
        return "\n\n".join(parts)

    @property
    def total_tokens(self) -> int:
        return sum(s.token_count for s in self.sections)

    def section_names(self) -> list[str]:
        return [s.name for s in self.sections]
