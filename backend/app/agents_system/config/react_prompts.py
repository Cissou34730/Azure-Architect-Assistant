"""
ReAct prompts and templates for the Azure Architect Assistant.

IMPORTANT: Prompts are now loaded from YAML files for easy editing.
Edit backend/config/prompts/agent_prompts.yaml to update prompts.
Changes take effect on next agent initialization.

This module provides backward-compatible access to prompts.
"""

import logging
from typing import Any

from .prompt_loader import (
    get_clarification_prompt,
    get_conflict_resolution_prompt,
    get_prompt_loader,
    get_react_template,
    get_system_prompt,
    reload_prompts,
)

logger = logging.getLogger(__name__)


def _format_few_shot_examples(examples: list[dict[str, Any]]) -> str:
    """Format few-shot examples defensively to avoid import-time KeyErrors."""
    formatted: list[str] = []
    for i, ex in enumerate(examples):
        if not isinstance(ex, dict):
            logger.warning("Skipping invalid few-shot example at index %s (not a mapping)", i)
            continue
        name = str(ex.get("name") or f"Example {i + 1}")
        question = str(ex.get("question") or "")
        reasoning = str(ex.get("reasoning") or "")
        formatted.append(f"Example {i + 1}: {name}\nQuestion: {question}\n{reasoning}".strip())
    return "\n\n".join(formatted)


# Load prompts from YAML file
SYSTEM_PROMPT = get_system_prompt()
REACT_TEMPLATE = get_react_template()
CLARIFICATION_PROMPT = get_clarification_prompt()
CONFLICT_RESOLUTION_PROMPT = get_conflict_resolution_prompt()

# Keep FEW_SHOT_EXAMPLES as formatted string for backward compatibility
_loader = get_prompt_loader()
_examples = _loader.get_few_shot_examples()

FEW_SHOT_EXAMPLES = _format_few_shot_examples(_examples)


__all__ = [
    "CLARIFICATION_PROMPT",
    "CONFLICT_RESOLUTION_PROMPT",
    "FEW_SHOT_EXAMPLES",
    "REACT_TEMPLATE",
    "SYSTEM_PROMPT",
    "get_prompt_loader",
    "reload_prompts",
]

