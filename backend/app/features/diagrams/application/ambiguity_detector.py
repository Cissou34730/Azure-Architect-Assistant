"""Ambiguity detection service for architecture descriptions.

Analyzes input descriptions using LLM to identify unclear or ambiguous elements
that could lead to incorrect diagram generation (FR-004, FR-019).
"""

import logging
from typing import Any

from .llm_client import DiagramLLMClient
from .prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

# Constants for validation logic
MIN_DESCRIPTION_LENGTH = 10
MIN_AMBIGUITY_TEXT_LENGTH = 5


class AmbiguityDetector:
    """Service for detecting ambiguities in architecture descriptions."""

    def __init__(self, llm_client: DiagramLLMClient) -> None:
        """Initialize ambiguity detector with LLM client.

        Args:
            llm_client: Diagram-specific LLM client for analysis
        """
        self.llm_client: DiagramLLMClient = llm_client
        self.prompt_builder: PromptBuilder = PromptBuilder()

    async def analyze_description(self, description: str) -> list[dict[str, Any]]:
        """Analyze input description and identify ambiguous elements.

        Uses LLM to detect:
        - Vague component names ("the system", "the service")
        - Unclear relationships ("communicates with", "uses")
        - Missing specifications (no technology, no protocols)
        - Ambiguous requirements (unclear behavior)

        Args:
            description: Architecture or functional requirements description

        Returns:
            List of ambiguity reports with:
            - ambiguous_text: Excerpt from description
            - reason: Why it's ambiguous
            - suggested_clarification: Recommended clarification question

        Example:
            [
                {
                    "ambiguous_text": "processes the document",
                    "reason": "Processing method not specified",
                    "suggested_clarification": "Specify: OCR extraction, NLP analysis, or text parsing?"
                }
            ]
        """
        logger.info(
            "Analyzing description for ambiguities (length: %d chars)", len(description)
        )

        if not description or len(description) < MIN_DESCRIPTION_LENGTH:
            logger.warning(
                "Description too short for analysis: %d chars", len(description)
            )
            return []

        try:
            # Build ambiguity detection prompt
            prompt = self.prompt_builder.build_ambiguity_prompt(description)

            # Call LLM to detect ambiguities (returns {"ambiguities": [...]})
            result = await self.llm_client.detect_ambiguities(prompt, temperature=0.4)
            ambiguities = result.get("ambiguities", [])

            logger.info("Detected %d ambiguities in description", len(ambiguities))

            # Validate and clean up results
            validated_ambiguities = self._validate_ambiguities(ambiguities, description)

            return validated_ambiguities

        except Exception as e:
            logger.error(
                "Failed to analyze description for ambiguities: %s",
                str(e),
                exc_info=True,
            )
            # Non-fatal error - return empty list to allow diagram generation to proceed
            return []

    def _map_ambiguity_fields(self, ambiguity: dict[str, Any]) -> None:
        """Map LLM-specific field names to internal service schema."""
        mapping = {
            "text": "ambiguous_text",
            "issue": "reason",
            "clarification": "suggested_clarification",
        }
        for llm_key, internal_key in mapping.items():
            if llm_key in ambiguity and internal_key not in ambiguity:
                ambiguity[internal_key] = ambiguity[llm_key]

    def _is_ambiguity_acceptable(
        self, ambiguity: dict[str, Any], original: str
    ) -> bool:
        """Check if ambiguity is grounded in original text and well-formed."""
        text = str(ambiguity.get("ambiguous_text", "")).strip()

        required_keys = ["ambiguous_text", "suggested_clarification"]
        if not all(k in ambiguity for k in required_keys):
            return False

        if not text or text not in original:
            return False

        return len(text) >= MIN_AMBIGUITY_TEXT_LENGTH

    def _validate_ambiguities(
        self, ambiguities: list[dict[str, Any]], original_description: str
    ) -> list[dict[str, Any]]:
        """Validate LLM-detected ambiguities against grounded description."""
        validated: list[dict[str, Any]] = []
        seen_texts: set[str] = set()

        for ambiguity in ambiguities:
            self._map_ambiguity_fields(ambiguity)

            if not self._is_ambiguity_acceptable(ambiguity, original_description):
                continue

            ambiguous_text = ambiguity["ambiguous_text"].strip()
            if ambiguous_text in seen_texts:
                continue

            seen_texts.add(ambiguous_text)
            validated.append(
                {
                    "ambiguous_text": ambiguous_text,
                    "suggested_clarification": ambiguity[
                        "suggested_clarification"
                    ].strip(),
                    "reason": (ambiguity.get("reason") or "").strip() or None,
                }
            )

        logger.info("Validated %d of %d ambiguities", len(validated), len(ambiguities))
        return validated

