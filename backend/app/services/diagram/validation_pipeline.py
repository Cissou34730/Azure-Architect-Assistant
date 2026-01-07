"""Validation pipeline orchestrator (Layers 1-5).

Coordinates all diagram validation layers before storage.
"""

import logging
from typing import Optional, List
from dataclasses import dataclass

from .syntax_validator import SyntaxValidator, ValidationResult
from .semantic_validator import SemanticValidator, SemanticValidationResult
from .visual_quality_checker import VisualQualityChecker, QualityReport
from .c4_compliance_validator import C4ComplianceValidator, C4ValidationResult
from .llm_client import DiagramLLMClient
from app.models.diagram import DiagramType

logger = logging.getLogger(__name__)


@dataclass
class PipelineValidationResult:
    """Combined result from all validation layers."""

    is_valid: bool
    syntax_result: Optional[ValidationResult] = None
    semantic_result: Optional[SemanticValidationResult] = None
    quality_report: Optional[QualityReport] = None
    c4_result: Optional[C4ValidationResult] = None
    error_message: Optional[str] = None
    retry_feedback: Optional[str] = None  # Feedback for LLM retry

    def __bool__(self) -> bool:
        return self.is_valid


class ValidationPipeline:
    """Orchestrates 5-layer validation pipeline for diagrams."""

    def __init__(
        self, llm_client: DiagramLLMClient, plantuml_jar_path: Optional[str] = None
    ) -> None:
        """Initialize validation pipeline with validators.

        Args:
            llm_client: Diagram-specific LLM client for semantic validation
            plantuml_jar_path: Path to PlantUML JAR (unused - remote rendering)
        """
        self.syntax_validator: SyntaxValidator = SyntaxValidator()
        self.semantic_validator: SemanticValidator = SemanticValidator(llm_client)
        self.c4_validator: C4ComplianceValidator = C4ComplianceValidator()
        self.quality_checker: VisualQualityChecker = VisualQualityChecker()
        self.plantuml_jar_path: Optional[str] = plantuml_jar_path

    async def validate_diagram(
        self, diagram_source: str, diagram_type: DiagramType, input_description: str
    ) -> PipelineValidationResult:
        """Run full validation pipeline on generated diagram.

        Pipeline order:
        1. Layer 1: Syntax Validation (BLOCKING)
        2. Layer 2: Semantic Validation (BLOCKING) - LLM checks accuracy
        3. Layer 3: Visual Quality (NON-BLOCKING) - logs warnings only
        4. Layer 4: C4 Compliance (BLOCKING for C4 diagrams) - deferred to Phase 4
        5. Layer 5: Azure Icon Validation (NON-BLOCKING for PlantUML) - deferred to Phase 5

        Args:
            diagram_source: Generated diagram source code
            diagram_type: Type of diagram
            input_description: Original description for semantic validation

        Returns:
            PipelineValidationResult with all layer results and retry feedback
        """
        logger.info("Running validation pipeline for %s diagram", diagram_type.value)

        # Layer 1: Syntax Validation (BLOCKING)
        syntax_result = await self._validate_syntax(diagram_source, diagram_type)
        if not syntax_result.is_valid:
            logger.error("Layer 1 (Syntax) failed: %s", syntax_result.error)
            return PipelineValidationResult(
                is_valid=False,
                syntax_result=syntax_result,
                error_message=f"Syntax error: {syntax_result.error}",
                retry_feedback=self._build_syntax_retry_feedback(syntax_result),
            )

        # Layer 2: Semantic Validation (BLOCKING)
        semantic_result = await self.semantic_validator.validate_diagram_semantics(
            input_description=input_description,
            diagram_source=diagram_source,
            diagram_type=diagram_type,
        )
        if not semantic_result.is_valid:
            logger.error(
                "Layer 2 (Semantic) failed: %d missing, %d incorrect",
                len(semantic_result.missing_elements),
                len(semantic_result.incorrect_relationships),
            )
            return PipelineValidationResult(
                is_valid=False,
                syntax_result=syntax_result,
                semantic_result=semantic_result,
                error_message="Semantic validation failed: diagram doesn't match description",
                retry_feedback=self._build_semantic_retry_feedback(semantic_result),
            )

        # Layer 3: Visual Quality (NON-BLOCKING)
        quality_report = await self._check_visual_quality(diagram_source, diagram_type)
        # Log warnings but don't block
        if quality_report.warnings:
            logger.warning(
                "Layer 3 (Quality) warnings: %s", "; ".join(quality_report.warnings)
            )
        if quality_report.issues:
            logger.warning(
                "Layer 3 (Quality) issues: %s", "; ".join(quality_report.issues)
            )

        # Layer 4: C4 Compliance (BLOCKING for C4 diagrams)
        c4_result = await self.c4_validator.validate_c4_compliance(
            diagram_source=diagram_source, diagram_type=diagram_type
        )
        if not c4_result.is_valid:
            logger.error("Layer 4 (C4 Compliance) failed: %s", c4_result.violations)
            return PipelineValidationResult(
                is_valid=False,
                syntax_result=syntax_result,
                semantic_result=semantic_result,
                quality_report=quality_report,
                c4_result=c4_result,
                error_message=f"C4 compliance violations: {'; '.join(c4_result.violations)}",
                retry_feedback=self._build_c4_retry_feedback(c4_result),
            )

        # Layer 5: Azure Icon Validation - deferred to Phase 5 (US3)
        # TODO T050: Add Azure icon validation for plantuml_azure type

        logger.info("Validation pipeline passed (all blocking layers)")
        return PipelineValidationResult(
            is_valid=True,
            syntax_result=syntax_result,
            semantic_result=semantic_result,
            quality_report=quality_report,
            c4_result=c4_result,
        )

    async def _validate_syntax(
        self, diagram_source: str, diagram_type: DiagramType
    ) -> ValidationResult:
        """Run Layer 1: Syntax validation.

        Args:
            diagram_source: Diagram source code
            diagram_type: Diagram type

        Returns:
            ValidationResult from syntax validator
        """
        if diagram_type == DiagramType.PLANTUML_AZURE:
            return await self.syntax_validator.validate_plantuml_syntax(
                diagram_source, self.plantuml_jar_path or ""
            )
        else:
            # Mermaid types: mermaid_functional, c4_context, c4_container
            return await self.syntax_validator.validate_mermaid_syntax(diagram_source)

    async def _check_visual_quality(
        self, diagram_source: str, diagram_type: DiagramType
    ) -> QualityReport:
        """Run Layer 3: Visual quality checks.

        Args:
            diagram_source: Diagram source code
            diagram_type: Diagram type

        Returns:
            QualityReport (non-blocking)
        """
        # Only check Mermaid diagrams for now
        if diagram_type != DiagramType.PLANTUML_AZURE:
            return await self.quality_checker.check_mermaid_visual_quality(
                diagram_source
            )

        # PlantUML quality checks deferred
        return QualityReport(
            is_acceptable=True, issues=[], warnings=[], severity="INFO", metrics={}
        )

    def _build_syntax_retry_feedback(self, syntax_result: ValidationResult) -> str:
        """Build retry feedback for syntax errors.

        Args:
            syntax_result: Failed syntax validation

        Returns:
            Feedback string for LLM retry prompt
        """
        feedback = f"Syntax error: {syntax_result.error}"
        if syntax_result.error_line:
            feedback += f" (line {syntax_result.error_line})"
        return feedback

    def _build_semantic_retry_feedback(
        self, semantic_result: SemanticValidationResult
    ) -> str:
        """Build retry feedback for semantic errors.

        Args:
            semantic_result: Failed semantic validation

        Returns:
            Feedback string for LLM retry prompt
        """
        feedback_parts: List[str] = []

        if semantic_result.missing_elements:
            feedback_parts.append(
                f"Missing elements: {', '.join(semantic_result.missing_elements)}"
            )

        if semantic_result.incorrect_relationships:
            feedback_parts.append(
                f"Incorrect relationships: {', '.join(semantic_result.incorrect_relationships)}"
            )

        if semantic_result.suggestions:
            feedback_parts.append(f"Suggestions: {semantic_result.suggestions}")

        return "; ".join(feedback_parts)

    def _build_c4_retry_feedback(self, c4_result: C4ValidationResult) -> str:
        """Build retry feedback for C4 compliance violations.

        Args:
            c4_result: Failed C4 validation

        Returns:
            Feedback string for LLM retry prompt
        """
        if not c4_result.violations:
            return "C4 compliance validation failed"

        feedback = "C4 compliance violations:\n" + "\n".join(
            f"- {violation}" for violation in c4_result.violations
        )
        return feedback
