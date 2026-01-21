"""
Minimal agent protocol to standardize agent interfaces.
"""

from typing import Any, Protocol


class Agent(Protocol):
    async def initialize(self) -> None:
        """Prepare agent internals before use."""
        ...

    async def execute(
        self, user_query: str, project_context: str | None = None
    ) -> dict[str, Any]:
        """Execute the agent for a query and return a structured result."""
        ...

