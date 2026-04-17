"""Syntax validation service for diagram source code (Layer 1 validation).

Validates diagram syntax before storage to catch errors early and enable retry logic.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of syntax validation."""

    is_valid: bool
    error: str | None = None
    error_line: int | None = None

    def __bool__(self) -> bool:
        return self.is_valid


class SyntaxValidator:
    """Validates diagram syntax for Mermaid and PlantUML."""

    _valid_mermaid_types: tuple[str, ...] = (
        "flowchart",
        "graph",
        "sequenceDiagram",
        "classDiagram",
        "stateDiagram",
        "erDiagram",
        "journey",
        "gantt",
        "pie",
        "C4Context",
        "C4Container",
        "C4Component",
        "C4Dynamic",
        "C4Deployment",
    )

    def detect_mermaid_diagram_type(self, source_code: str) -> str | None:
        """Return the Mermaid diagram type declared on the first non-empty line."""
        for raw_line in source_code.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            for diagram_type in self._valid_mermaid_types:
                if line.startswith(diagram_type):
                    return diagram_type
            return None
        return None

    def _first_content_line_number(self, source_code: str) -> int | None:
        for line_number, raw_line in enumerate(source_code.splitlines(), start=1):
            if raw_line.strip():
                return line_number
        return None

    def _line_number_for_offset(self, source_code: str, offset: int) -> int:
        return source_code[:offset].count("\n") + 1

    def _find_balanced_bracket_error(
        self, source_code: str
    ) -> tuple[str, int] | None:
        brackets: dict[str, str] = {"[": "]", "(": ")", "{": "}"}
        stack: list[tuple[str, int]] = []
        for index, char in enumerate(source_code):
            if char in brackets:
                stack.append((char, index))
                continue
            if char not in brackets.values():
                continue
            if not stack:
                return (
                    f"Unmatched closing bracket '{char}' at position {index}",
                    self._line_number_for_offset(source_code, index),
                )
            opening, opening_index = stack.pop()
            if brackets[opening] != char:
                return (
                    f"Mismatched brackets: '{opening}' closed with '{char}'",
                    self._line_number_for_offset(source_code, opening_index),
                )

        if not stack:
            return None
        opening, opening_index = stack[-1]
        return (
            f"Unclosed bracket '{opening}' opened at position {opening_index}",
            self._line_number_for_offset(source_code, opening_index),
        )

    async def validate_mermaid_syntax(self, source_code: str) -> ValidationResult:
        """Validate Mermaid diagram syntax.

        Note: Using basic pattern matching since pyproject-mermaid package doesn't exist.
        For production, integrate mermaid-cli (mmdc) or use frontend validation only.

        Args:
            source_code: Mermaid source code

        Returns:
            ValidationResult with is_valid flag and error message if invalid
        """
        logger.info("Validating Mermaid syntax (length: %d chars)", len(source_code))

        if not source_code or not source_code.strip():
            return ValidationResult(is_valid=False, error="Empty source code")

        # Basic syntax checks (expand as needed)
        errors: list[str] = []

        # Check for required diagram type declaration
        detected_type = self.detect_mermaid_diagram_type(source_code)
        first_content_line = self._first_content_line_number(source_code)

        if detected_type is None:
            errors.append(
                f"Missing diagram type declaration. First line must be one of: {', '.join(self._valid_mermaid_types)}"
            )
            error_line = first_content_line
        else:
            error_line = None

        # Check for balanced brackets/parentheses
        bracket_error = self._find_balanced_bracket_error(source_code)
        if bracket_error is not None:
            message, bracket_line = bracket_error
            errors.append(message)
            error_line = error_line or bracket_line

        # Check for basic syntax patterns in flowcharts
        if detected_type in {"flowchart", "graph"} and "-->" not in source_code and "---" not in source_code:
            logger.warning("Flowchart contains no arrows (might be incomplete)")

        if errors:
            error_msg = "; ".join(errors)
            logger.warning("Mermaid syntax validation failed: %s", error_msg)
            return ValidationResult(is_valid=False, error=error_msg, error_line=error_line)

        logger.info("Mermaid syntax validation passed")
        return ValidationResult(is_valid=True)

    async def validate_plantuml_syntax(
        self, source_code: str, plantuml_jar_path: str
    ) -> ValidationResult:
        """Validate PlantUML diagram syntax using PlantUML JAR.

        NOTE: Currently deferred - Java/PlantUML JAR not deployed in this environment.
        Will use remote rendering service (Kroki/PlantUML Server) in Phase 5.

        Args:
            source_code: PlantUML source code
            plantuml_jar_path: Path to plantuml.jar (unused for now)

        Returns:
            ValidationResult (always valid for now - defer to remote service)
        """
        logger.warning(
            "PlantUML syntax validation deferred - using remote rendering in Phase 5"
        )

        # Basic checks only (real validation happens in remote service)
        if not source_code or not source_code.strip():
            return ValidationResult(is_valid=False, error="Empty source code")

        if "@startuml" not in source_code or "@enduml" not in source_code:
            return ValidationResult(
                is_valid=False,
                error="PlantUML must start with @startuml and end with @enduml",
            )

        # TODO Phase 5: Validate via Kroki API or PlantUML Server
        # For now, assume valid if basic structure present
        logger.info("PlantUML basic structure validated (full validation deferred)")
        return ValidationResult(is_valid=True)

