"""
ReAct prompts and templates for the Azure Architect Assistant.

IMPORTANT: Prompts are now loaded from YAML files for easy editing.
Edit backend/config/prompts/agent_prompts.yaml to update prompts.
Changes take effect on next agent initialization.

This module provides backward-compatible access to prompts.
"""

from .prompt_loader import (
    get_clarification_prompt,
    get_conflict_resolution_prompt,
    get_prompt_loader,
    get_react_template,
    get_system_prompt,
    reload_prompts,
)

# Load prompts from YAML file
SYSTEM_PROMPT = get_system_prompt()
REACT_TEMPLATE = get_react_template()
CLARIFICATION_PROMPT = get_clarification_prompt()
CONFLICT_RESOLUTION_PROMPT = get_conflict_resolution_prompt()

# Keep FEW_SHOT_EXAMPLES as formatted string for backward compatibility
_loader = get_prompt_loader()
_examples = _loader.get_few_shot_examples()

FEW_SHOT_EXAMPLES = "\n\n".join(
    [
        f"Example {i + 1}: {ex['name']}\nQuestion: {ex['question']}\n{ex['reasoning']}"
        for i, ex in enumerate(_examples)
    ]
)


__all__ = [
    "CLARIFICATION_PROMPT",
    "CONFLICT_RESOLUTION_PROMPT",
    "FEW_SHOT_EXAMPLES",
    "REACT_TEMPLATE",
    "SYSTEM_PROMPT",
    "get_prompt_loader",
    "reload_prompts",
]

