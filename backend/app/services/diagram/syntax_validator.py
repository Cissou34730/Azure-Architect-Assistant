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

    def _check_balanced_brackets(self, source_code: str) -> list[str]:
        """Check for balanced brackets/parentheses."""
        errors: list[str] = []
        brackets: dict[str, str] = {"[": "]", "(": ")", "{": "}"}
        stack: list[tuple[str, int]] = []
        for i, char in enumerate(source_code):
            if char in brackets:
                stack.append((char, i))
            elif char in brackets.values():
                if not stack:
                    errors.append(f"Unmatched closing bracket '{char}' at position {i}")
                    break
                opening, _ = stack.pop()
                if brackets[opening] != char:
                    errors.append(
                        f"Mismatched brackets: '{opening}' closed with '{char}'"
                    )
                    break

        if stack:
            opening, pos = stack[-1]
            errors.append(f"Unclosed bracket '{opening}' opened at position {pos}")
        return errors

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
        first_line: str = source_code.strip().split("\n")[0].strip()
        valid_types: list[str] = [
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
        ]

        if not any(first_line.startswith(t) for t in valid_types):
            errors.append(
                f"Missing diagram type declaration. First line must be one of: {', '.join(valid_types)}"
            )

        # Check for balanced brackets/parentheses
        errors.extend(self._check_balanced_brackets(source_code))

        # Check for basic syntax patterns in flowcharts
        if first_line.startswith(("flowchart", "graph")) and "-->" not in source_code and "---" not in source_code:
            logger.warning("Flowchart contains no arrows (might be incomplete)")

        if errors:
            error_msg = "; ".join(errors)
            logger.warning("Mermaid syntax validation failed: %s", error_msg)
            return ValidationResult(is_valid=False, error=error_msg)

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

