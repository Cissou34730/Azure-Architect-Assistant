"""Utilities to sanitize machine-only payload blocks from agent output."""

from __future__ import annotations

import re

_AAA_MACHINE_BLOCK_PATTERNS = (
    re.compile(
        r"(?:^|\n)\s*AAA_STATE_UPDATE:?\s*```json\s*.*?```(?:\n|$)",
        re.DOTALL,
    ),
    re.compile(
        r"(?:^|\n)\s*AAA_MCP_LOG:?\s*```json\s*.*?```(?:\n|$)",
        re.DOTALL,
    ),
)

_REACT_TRACE_PATTERNS = (
    # Fenced ReAct trace leak such as ```Thought: ... Action: ...```
    re.compile(
        r"(?:^|\n)\s*```(?:[a-zA-Z0-9_-]+)?\s*(?:Thought:|Action:|Observation:).*?```(?:\n|$)",
        re.DOTALL | re.IGNORECASE,
    ),
    # Unfenced ReAct scratchpad blocks (without Final Answer)
    re.compile(
        r"(?:^|\n)\s*Thought:\s.*?\n\s*Action:\s.*?\n\s*Action Input:\s.*?(?=(?:\n\s*Final Answer:|\Z))",
        re.DOTALL | re.IGNORECASE,
    ),
)


def sanitize_agent_output(text: str) -> str:
    """Remove machine-readable payload blocks from user-facing assistant content."""
    if not text:
        return ""

    cleaned = text
    for pattern in _AAA_MACHINE_BLOCK_PATTERNS:
        cleaned = pattern.sub("\n", cleaned)
    for pattern in _REACT_TRACE_PATTERNS:
        cleaned = pattern.sub("\n", cleaned)

    # Remove parser artifacts sometimes left before leaked traces.
    cleaned = re.sub(r"^\s*\{\s*\}\s*$", "", cleaned, flags=re.MULTILINE)

    # Normalize excess blank lines after block removal.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()

