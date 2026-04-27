"""Semantic validation service (Layer 2 validation).

Verifies that generated diagrams accurately represent the input description,
not just syntactically correct.

Also exposes :func:`validate_diagram_semantics` — a **pure, non-LLM, non-blocking**
heuristic checker that surfaces structural quality warnings without blocking
the generation pipeline.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.features.diagrams.infrastructure.models import DiagramType

from .llm_client import DiagramLLMClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public standalone helper (no LLM, non-blocking)
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(
    r"\b(TODO|PLACEHOLDER|EXAMPLE|FIXME|TBD|FILL_?IN)\b", re.IGNORECASE
)
_UNLABELED_ARROW_RE = re.compile(r"--\s*>(?!\s*\|)")  # --> not followed by |label|
_BARE_ABBREVIATION_RE = re.compile(
    r"(?<!['\"\w])(?:DB|SVC|API|SRV|BE|FE|UI)(?!['\"\w\[\(\{])"
)
# C4 actor keywords
_ACTOR_RE = re.compile(r"\bPerson\s*\(", re.IGNORECASE)
# C4 boundary / system presence
_SYSTEM_RE = re.compile(r"\b(?:System|Container|Boundary)\s*\(", re.IGNORECASE)
# External dependencies in container diagrams
_EXTERNAL_RE = re.compile(
    r"\b(?:System_Ext|Container_Ext|External)\s*\(", re.IGNORECASE
)


def validate_diagram_semantics(diagram_code: str, diagram_type: str) -> list[str]:
    """Check a diagram for common quality issues without calling an LLM.

    This function is **non-blocking**: it returns a list of human-readable warning
    strings (empty list = no issues).  It never raises; bad input yields warnings.

    Args:
        diagram_code: Raw source code of the diagram (Mermaid or C4 PlantUML).
        diagram_type: One of ``"c4_context"``, ``"c4_container"``,
            ``"mermaid_functional"``, or any other string (unknown types are
            checked only for generic rules).

    Returns:
        A (possibly empty) list of warning strings.
    """
    warnings: list[str] = []

    if not diagram_code or not diagram_code.strip():
        warnings.append("Diagram is empty — no content to render.")
        return warnings

    code = diagram_code

    # --- Generic checks (all diagram types) ---

    if _PLACEHOLDER_RE.search(code):
        warnings.append(
            "Diagram contains placeholder text (TODO / PLACEHOLDER / EXAMPLE). "
            "Replace with real architecture content."
        )

    # --- Type-specific checks ---

    if diagram_type == "c4_context":
        if not _ACTOR_RE.search(code):
            warnings.append(
                "C4 Context diagram has no Person/actor node. "
                "Add at least one Person() to represent a user or external actor."
            )
        if not _SYSTEM_RE.search(code):
            warnings.append(
                "C4 Context diagram appears to have no System or Boundary elements. "
                "Ensure at least one System() is present."
            )

    elif diagram_type == "c4_container":
        if not _EXTERNAL_RE.search(code):
            warnings.append(
                "C4 Container diagram shows no external dependencies (System_Ext / Container_Ext). "
                "Show at least one external system or service to provide context."
            )

    elif diagram_type == "mermaid_functional":
        if _UNLABELED_ARROW_RE.search(code):
            warnings.append(
                "Some Mermaid arrows appear to lack labels. "
                "Label data flows (e.g. --> |\"HTTP request\"|) to clarify interactions."
            )
        if _BARE_ABBREVIATION_RE.search(code):
            warnings.append(
                "Some nodes use bare abbreviations (DB, API, SVC, …). "
                "Use descriptive names (e.g. 'Azure SQL Database' instead of 'DB')."
            )

    return warnings


@dataclass
class SemanticValidationResult:
    """Result of semantic validation."""

    is_valid: bool
    missing_elements: list[str]
    incorrect_relationships: list[str]
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
                suggestions=f"Validation error (non-blocking): {e!s}",
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

        # Add type-specific guidance
        type_guidance = ""
        if diagram_type == DiagramType.C4_CONTEXT:
            type_guidance = """
IMPORTANT FOR C4 CONTEXT DIAGRAMS:
- Focus ONLY on systems, external actors, and their relationships
- NFRs (performance, security, compliance) should NOT be visual elements
- Do NOT expect database schemas, deployment details, or implementation specifics
- Missing NFR representations (like "PCI DSS", "99.9% SLA", "global coverage") is ACCEPTABLE
- Only mark as invalid if key SYSTEMS or ACTORS are missing
"""
        elif diagram_type == DiagramType.C4_CONTAINER:
            type_guidance = """
IMPORTANT FOR C4 CONTAINER DIAGRAMS:
- Focus on containers (applications, data stores, microservices)
- External systems should be shown as System_Ext
- Do NOT expect component-level details (wrong abstraction level)
"""

        prompt: str = f"""Compare the input description with the generated diagram to verify accuracy.

INPUT DESCRIPTION:
{description}

DIAGRAM TYPE: {diagram_type_name}
DIAGRAM CODE:
{diagram_source}
{type_guidance}
Verify the following:
1. Are all mentioned SYSTEMS/ACTORS present in the diagram?
2. Are relationships correctly represented?
3. Is the abstraction level appropriate for {diagram_type_name}?
4. Are any significant elements missing or incorrectly depicted?

Return JSON with:
{{
  "is_valid": true/false,
  "missing_elements": ["element1", "element2"],
  "incorrect_relationships": ["issue1", "issue2"],
  "suggestions": "Specific recommendations for fixing issues"
}}

Be reasonable: mark as invalid only if KEY systems/actors are missing or relationships are fundamentally wrong.
"""
        return prompt

    def _parse_validation_result(self, llm_response: str) -> dict[str, Any]:
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
            result: dict[str, Any] = json.loads(llm_response)

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
                "suggestions": f"Validation parsing error: {e!s}",
            }

