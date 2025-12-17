"""Diagram generation service with retry logic and validation.

Orchestrates LLM-powered diagram generation with validation pipeline.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from .llm_client import DiagramLLMClient
from .prompt_builder import PromptBuilder
from .validation_pipeline import ValidationPipeline, PipelineValidationResult
from app.models.diagram import DiagramType

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result of diagram generation attempt."""
    success: bool
    source_code: Optional[str] = None
    diagram_type: DiagramType = None
    attempts: int = 0
    validation_result: Optional[PipelineValidationResult] = None
    error: Optional[str] = None


class DiagramGenerator:
    """Generates diagrams from text descriptions with validation and retry."""

    MAX_RETRIES = 3  # Per FR-021

    def __init__(self, llm_client: DiagramLLMClient):
        """Initialize diagram generator.
        
        Args:
            llm_client: Diagram-specific LLM client
        """
        self.llm_client = llm_client
        self.prompt_builder = PromptBuilder()
        # Note: plantuml_jar_path deferred to Phase 5 (remote rendering)
        self.validation_pipeline = ValidationPipeline(
            llm_client=llm_client,
            plantuml_jar_path=None
        )

    async def generate_mermaid_functional(
        self,
        description: str,
        max_retries: Optional[int] = None
    ) -> GenerationResult:
        """Generate Mermaid functional flow diagram.
        
        Uses flowchart syntax with TD (top-down) direction.
        Max 20 nodes for readability.
        
        Args:
            description: Functional requirements description
            max_retries: Override default max retries (default: 3)
            
        Returns:
            GenerationResult with source code or error
        """
        logger.info("Generating Mermaid functional diagram (description: %d chars)", len(description))
        
        diagram_type = DiagramType.MERMAID_FUNCTIONAL
        return await self._generate_with_retry(
            description=description,
            diagram_type=diagram_type,
            max_retries=max_retries or self.MAX_RETRIES
        )

    async def _generate_with_retry(
        self,
        description: str,
        diagram_type: DiagramType,
        max_retries: int
    ) -> GenerationResult:
        """Generate diagram with validation and retry loop.
        
        Flow:
        1. Generate diagram using LLM
        2. Validate using validation pipeline
        3. If validation fails:
           a. Include error feedback in retry prompt
           b. Retry up to max_retries times
        4. Return final result (success or failure after retries)
        
        Args:
            description: Input description
            diagram_type: Type of diagram to generate
            max_retries: Maximum retry attempts
            
        Returns:
            GenerationResult with final outcome
        """
        previous_error: Optional[str] = None
        
        for attempt in range(1, max_retries + 1):
            logger.info("Generation attempt %d/%d for %s", attempt, max_retries, diagram_type.value)
            
            try:
                # Build prompt (includes retry feedback if not first attempt)
                prompt = self.prompt_builder.build_generation_prompt(
                    description=description,
                    diagram_type=diagram_type,
                    previous_error=previous_error
                )
                
                # Generate diagram via LLM
                diagram_source = await self.llm_client.generate_diagram(
                    prompt=prompt,
                    temperature=0.3
                )
                
                if not diagram_source:
                    logger.error("LLM returned empty diagram source")
                    previous_error = "LLM returned empty response"
                    continue
                
                # Validate generated diagram
                validation_result = await self.validation_pipeline.validate_diagram(
                    diagram_source=diagram_source,
                    diagram_type=diagram_type,
                    input_description=description
                )
                
                if validation_result.is_valid:
                    # Success!
                    logger.info(
                        "Diagram generated successfully on attempt %d/%d",
                        attempt, max_retries
                    )
                    return GenerationResult(
                        success=True,
                        source_code=diagram_source,
                        diagram_type=diagram_type,
                        attempts=attempt,
                        validation_result=validation_result
                    )
                
                # Validation failed - prepare retry feedback
                previous_error = validation_result.retry_feedback or validation_result.error_message
                logger.warning(
                    "Validation failed (attempt %d/%d): %s",
                    attempt, max_retries, previous_error
                )
                
            except Exception as e:
                logger.error(
                    "Generation error (attempt %d/%d): %s",
                    attempt, max_retries, str(e),
                    exc_info=True
                )
                previous_error = f"Generation exception: {str(e)}"
        
        # All retries exhausted
        logger.error(
            "Diagram generation failed after %d attempts for %s",
            max_retries, diagram_type.value
        )
        return GenerationResult(
            success=False,
            diagram_type=diagram_type,
            attempts=max_retries,
            error=f"Failed after {max_retries} attempts. Last error: {previous_error}"
        )
