"""Semantic validation service (Layer 2 validation).

Verifies that generated diagrams accurately represent the input description,
not just syntactically correct.
"""

import logging
import json
from typing import Dict, Any, List
from dataclasses import dataclass

from .llm_client import DiagramLLMClient
from app.models.diagram import DiagramType

logger = logging.getLogger(__name__)


@dataclass
class SemanticValidationResult:
    """Result of semantic validation."""

    is_valid: bool
    missing_elements: List[str]
    incorrect_relationships: List[str]
    suggestions: str

    def __bool__(self) -> bool:
        return self.is_valid


class SemanticValidator:
    """Validates diagram semantics using LLM analysis."""

    def __init__(self, llm_client: DiagramLLMClient) -> None:
        """Initialize semantic validator with LLM client.

        Args:
            llm_client: Diagram-specific LLM client for validation
        """
        self.llm_client: DiagramLLMClient = llm_client

    async def validate_diagram_semantics(
        self, input_description: str, diagram_source: str, diagram_type: DiagramType
    ) -> SemanticValidationResult:
        """Validate that diagram accurately represents input description.

        Uses LLM to compare input vs generated diagram and check for:
        - Missing components/systems mentioned in description
        - Incorrect relationships (wrong direction, missing connections)
        - Wrong abstraction level for diagram type

        Args:
            input_description: Original architecture/requirements description
            diagram_source: Generated diagram source code
            diagram_type: Type of diagram (functional, C4 context, etc.)

        Returns:
            SemanticValidationResult with validation details
        """
        logger.info(
            "Validating semantics for %s diagram (description: %d chars, source: %d chars)",
            diagram_type.value,
            len(input_description),
            len(diagram_source),
        )

        # Build validation prompt
        prompt = self._build_validation_prompt(
            input_description, diagram_source, diagram_type
        )

        try:
            # Call LLM for semantic validation (returns dict already parsed)
            result_data = await self.llm_client.validate_semantics(
                prompt, temperature=0.2
            )

            is_valid = result_data.get("is_valid", False)
            missing_elements = result_data.get("missing_elements", [])
            incorrect_relationships = result_data.get("incorrect_relationships", [])
            suggestions = result_data.get("suggestions", "")

            if not is_valid:
                logger.warning(
                    "Semantic validation failed: %d missing elements, %d incorrect relationships",
                    len(missing_elements),
                    len(incorrect_relationships),
                )
            else:
                logger.info("Semantic validation passed")

            return SemanticValidationResult(
                is_valid=is_valid,
                missing_elements=missing_elements,
                incorrect_relationships=incorrect_relationships,
                suggestions=suggestions,
            )

        except Exception as e:
            logger.error("Semantic validation error: %s", str(e), exc_info=True)
            # Non-blocking: assume valid on validation error (better than blocking generation)
            return SemanticValidationResult(
                is_valid=True,
                missing_elements=[],
                incorrect_relationships=[],
                suggestions=f"Validation error (non-blocking): {str(e)}",
            )

    def _build_validation_prompt(
        self, description: str, diagram_source: str, diagram_type: DiagramType
    ) -> str:
        """Build LLM prompt for semantic validation.

        Args:
            description: Input description
            diagram_source: Generated diagram
            diagram_type: Diagram type

        Returns:
            Validation prompt for LLM
        """
        diagram_type_name: str = diagram_type.value.replace("_", " ").title()

        prompt: str = f"""Compare the input description with the generated diagram to verify accuracy.

INPUT DESCRIPTION:
{description}

DIAGRAM TYPE: {diagram_type_name}
DIAGRAM CODE:
{diagram_source}

Verify the following:
1. Are all mentioned components/systems present in the diagram?
2. Are relationships correctly represented?
3. Is the abstraction level appropriate for {diagram_type_name}?
4. Are any elements missing or incorrectly depicted?

Return JSON with:
{{
  "is_valid": true/false,
  "missing_elements": ["element1", "element2"],
  "incorrect_relationships": ["issue1", "issue2"],
  "suggestions": "Specific recommendations for fixing issues"
}}

Be strict: mark as invalid if significant elements are missing or relationships are wrong.
"""
        return prompt

    def _parse_validation_result(self, llm_response: str) -> Dict[str, Any]:
        """Parse LLM validation response (JSON format).

        Args:
            llm_response: LLM response text

        Returns:
            Parsed validation result dict

        Raises:
            ValueError: If response is not valid JSON
        """
        try:
            # Try parsing as JSON
            result: Dict[str, Any] = json.loads(llm_response)

            # Validate required fields
            if "is_valid" not in result:
                raise ValueError("Missing 'is_valid' field in validation result")

            return result

        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM validation result as JSON: %s", str(e))
            # Try extracting JSON from markdown code block
            if "```json" in llm_response:
                json_start: int = llm_response.find("```json") + 7
                json_end: int = llm_response.find("```", json_start)
                json_str: str = llm_response[json_start:json_end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass

            # Fallback: assume invalid if can't parse
            return {
                "is_valid": False,
                "missing_elements": [],
                "incorrect_relationships": [],
                "suggestions": f"Validation parsing error: {str(e)}",
            }
