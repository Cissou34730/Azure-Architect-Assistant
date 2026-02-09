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


def sanitize_agent_output(text: str) -> str:
    """Remove machine-readable payload blocks from user-facing assistant content."""
    if not text:
        return ""

    cleaned = text
    for pattern in _AAA_MACHINE_BLOCK_PATTERNS:
        cleaned = pattern.sub("\n", cleaned)

    # Normalize excess blank lines after block removal.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()

