"""
Factories/registry for orchestrator dependencies (Phase 1).

Note: In Phase 1 this is a placeholder. In later phases this module will build
LLMs, prompts, tools, and summarize hooks for injection into agents.
"""

from typing import Tuple


def default_budgets() -> Tuple[int, int]:
    """Return (max_iterations, max_execution_time_seconds) defaults."""
    return (10, 60)
