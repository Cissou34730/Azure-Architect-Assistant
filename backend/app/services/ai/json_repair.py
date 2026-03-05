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
    except json.JSONDecodeError as first_error:
        logger.error("JSON decode failed: %s", first_error)
        logger.error("Response content (first %d chars): %s", preview_chars, content[:preview_chars])
        try:
            repaired_content = await repair_fn(content, max_tokens)
        except Exception as repair_err:
            raise ValueError("JSON repair callback raised an error") from repair_err
        try:
            return json.loads(repaired_content)
        except json.JSONDecodeError as second_error:
            logger.error(
                "Repaired JSON still invalid: %s | repaired=%s",
                second_error,
                repaired_content[:preview_chars],
            )
            raise ValueError("JSON repair produced invalid JSON") from second_error


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
    """Extract the first valid top-level JSON object or array from text.

    Tries ``{...}`` first, then ``[...]``.  Each candidate is validated with
    ``json.loads`` before being returned so callers can rely on the result
    being parseable.  Returns ``None`` if no valid candidate is found.
    """
    for open_char, close_char in ("{", "}"), ("[", "]"):
        start = response_text.find(open_char)
        if start == -1:
            continue
        end = response_text.rfind(close_char)
        if end == -1 or end <= start:
            continue
        candidate = response_text[start : end + 1]
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            continue
    return None
