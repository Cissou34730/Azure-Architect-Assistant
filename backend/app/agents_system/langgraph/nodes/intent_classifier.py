"""LLM-based artifact intent classification.

Uses a cheap LLM call to detect whether a user message intends to
create, update, or persist project artifacts. This replaces brittle
keyword-only detection with semantic understanding.

Design:
- System message for classification instructions (not user interpolation)
- JSON-mode response for reliable parsing
- Short timeout + safe fallback on any error
- Cheap token budget (≤128 tokens)
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field

from app.shared.ai.ai_service import get_ai_service
from app.shared.ai.interfaces import ChatMessage
from app.shared.config.app_settings import get_app_settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an intent classifier for an Azure architecture assistant.
Determine whether the user wants to CREATE, UPDATE, REMOVE, or REQUEST PERSISTENCE of any project artifacts.

Artifact types (use these exact names):
- requirement
- assumption
- clarification_question
- candidate_architecture
- diagram
- adr
- traceability
- validation_finding
- cost_estimate

Respond ONLY with JSON:
{"intent": true, "types": ["requirement", "assumption"]}
or
{"intent": false, "types": []}

Rules:
- "intent": true means the user wants artifacts to be created, modified, or persisted.
- "intent": false means the user is asking a question, requesting information, or chatting.
- Read-only requests like "show me the requirements" or "summarize assumptions" are NOT artifact intent.
- Creation requests like "add requirements", "state clarification questions", "generate assumptions" ARE artifact intent.
"""


@dataclass(frozen=True)
class ArtifactIntentResult:
    """Result of LLM-based artifact intent classification."""

    intent: bool = False
    types: list[str] = field(default_factory=list)


async def classify_artifact_intent(user_message: str) -> ArtifactIntentResult:
    """Classify whether a user message has artifact create/update intent.

    Uses a cheap LLM call with:
    - System message (not user interpolation) for classification
    - Low token budget (configurable via settings)
    - Short timeout (configurable via settings)
    - Safe fallback on any error → ArtifactIntentResult(intent=False)
    """
    settings = get_app_settings()
    max_tokens = settings.intent_classifier_max_tokens
    timeout_seconds = settings.intent_classifier_timeout_seconds

    try:
        ai_service = get_ai_service()
        messages = [
            ChatMessage(role="system", content=_SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_message),
        ]
        response = await asyncio.wait_for(
            ai_service.chat(
                messages=messages,
                temperature=0.0,
                max_tokens=max_tokens,
            ),
            timeout=timeout_seconds,
        )
        return _parse_response(response.content)

    except asyncio.TimeoutError:
        logger.warning(
            "Intent classifier timed out after %.1fs for message: %.80s",
            timeout_seconds,
            user_message,
        )
        return ArtifactIntentResult()

    except Exception:
        logger.warning(
            "Intent classifier failed for message: %.80s",
            user_message,
            exc_info=True,
        )
        return ArtifactIntentResult()


def _parse_response(content: str) -> ArtifactIntentResult:
    """Parse LLM JSON response into ArtifactIntentResult."""
    try:
        data = json.loads(content.strip())
        intent = bool(data.get("intent", False))
        raw_types = data.get("types", [])
        types = [t for t in raw_types if isinstance(t, str)]
        return ArtifactIntentResult(intent=intent, types=types)
    except (json.JSONDecodeError, TypeError, KeyError):
        logger.warning("Intent classifier returned unparseable response: %.200s", content)
        return ArtifactIntentResult()
