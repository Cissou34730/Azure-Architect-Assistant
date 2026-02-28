"""JSON parsing and repair utilities for LLM responses.

Extracted from llm_service.py to keep the repair logic testable in isolation.
"""

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


async def parse_json_with_repair(
    content: str,
    *,
    max_tokens: int,
    repair_fn: Callable[[str, int], Awaitable[str]],
    preview_chars: int = 500,
) -> dict[str, Any]:
    """Parse JSON content and attempt one repair pass on decode failure.

    Args:
        content: Raw string from LLM response.
        max_tokens: Token budget forwarded to the repair call.
        repair_fn: Async callable(invalid_json, max_tokens) → repaired JSON string.
        preview_chars: How many chars to log on error.
    """
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("JSON decode failed: %s", e)
        logger.error("Response content: %s", content[:preview_chars])
        repaired_content = await repair_fn(content, max_tokens)
        return json.loads(repaired_content)


async def repair_json_content(
    invalid_json: str,
    max_tokens: int,
    *,
    complete_fn: Callable[[str, str, int], Awaitable[str]],
) -> str:
    """Ask the model to repair malformed/truncated JSON.

    Args:
        invalid_json: The broken JSON string.
        max_tokens: Token budget for the repair request.
        complete_fn: Async callable(system_prompt, user_prompt, max_tokens) → str.

    Returns:
        A repaired JSON string.

    Raises:
        ValueError: If repair produces no JSON object.
    """
    repair_system_prompt = (
        "You are a strict JSON repair assistant. "
        "You receive malformed or truncated JSON. "
        "Return ONLY valid JSON with the same top-level structure and keys. "
        "Do not use markdown, comments, or code fences."
    )

    repair_user_prompt = (
        "Repair this invalid JSON and return valid JSON only.\n\n"
        f"{invalid_json}"
    )

    repaired = await complete_fn(repair_system_prompt, repair_user_prompt, max_tokens)

    repaired_candidate = extract_json_candidate(repaired)
    if repaired_candidate is None:
        logger.error("JSON repair failed: no JSON object found in repaired response")
        raise ValueError("JSON repair failed: no JSON object found")

    logger.info("Successfully repaired malformed JSON response")
    return repaired_candidate


def extract_json_candidate(response_text: str) -> str | None:
    """Extract the outer JSON object from text if present."""
    start = response_text.find("{")
    end = response_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return response_text[start : end + 1]
