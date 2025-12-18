"""Ambiguity detection service for architecture descriptions.

Analyzes input descriptions using LLM to identify unclear or ambiguous elements
that could lead to incorrect diagram generation (FR-004, FR-019).
"""

import logging
from typing import List, Dict, Any, Set

from .llm_client import DiagramLLMClient
from .prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class AmbiguityDetector:
    """Service for detecting ambiguities in architecture descriptions."""

    def __init__(self, llm_client: DiagramLLMClient) -> None:
        """Initialize ambiguity detector with LLM client.
        
        Args:
            llm_client: Diagram-specific LLM client for analysis
        """
        self.llm_client: DiagramLLMClient = llm_client
        self.prompt_builder: PromptBuilder = PromptBuilder()

    async def analyze_description(self, description: str) -> List[Dict[str, Any]]:
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
        logger.info("Analyzing description for ambiguities (length: %d chars)", len(description))
        
        if not description or len(description) < 10:
            logger.warning("Description too short for analysis: %d chars", len(description))
            return []
        
        try:
            # Build ambiguity detection prompt
            prompt = self.prompt_builder.build_ambiguity_prompt(description)
            
            # Call LLM to detect ambiguities
            ambiguities = await self.llm_client.detect_ambiguities(prompt, temperature=0.4)
            
            logger.info("Detected %d ambiguities in description", len(ambiguities))
            
            # Validate and clean up results
            validated_ambiguities = self._validate_ambiguities(ambiguities, description)
            
            return validated_ambiguities
            
        except Exception as e:
            logger.error("Failed to analyze description for ambiguities: %s", str(e), exc_info=True)
            # Non-fatal error - return empty list to allow diagram generation to proceed
            return []

    def _validate_ambiguities(
        self, 
        ambiguities: List[Dict[str, Any]], 
        original_description: str
    ) -> List[Dict[str, Any]]:
        """Validate LLM-detected ambiguities against original description.
        
        Filters out:
        - Ambiguities with text not present in original description
        - Duplicate ambiguities (same ambiguous_text)
        - Ambiguities with missing required fields
        
        Args:
            ambiguities: Raw LLM output
            original_description: Original input description for validation
            
        Returns:
            Filtered and validated ambiguity list
        """
        validated: List[Dict[str, Any]] = []
        seen_texts: Set[str] = set()
        
        for ambiguity in ambiguities:
            # Check required fields
            if not all(k in ambiguity for k in ["ambiguous_text", "suggested_clarification"]):
                logger.warning("Skipping ambiguity with missing fields: %s", ambiguity)
                continue
            
            ambiguous_text = ambiguity.get("ambiguous_text", "").strip()
            
            # Skip if text not in original description (hallucination)
            if ambiguous_text not in original_description:
                logger.warning("Skipping hallucinated ambiguity: '%s'", ambiguous_text)
                continue
            
            # Skip duplicates
            if ambiguous_text in seen_texts:
                logger.debug("Skipping duplicate ambiguity: '%s'", ambiguous_text)
                continue
            
            # Skip if ambiguous text is too short (likely noise)
            if len(ambiguous_text) < 5:
                logger.debug("Skipping too-short ambiguity: '%s'", ambiguous_text)
                continue
            
            seen_texts.add(ambiguous_text)
            validated.append({
                "ambiguous_text": ambiguous_text,
                "suggested_clarification": ambiguity.get("suggested_clarification", "").strip(),
                "reason": ambiguity.get("reason", "").strip() or None
            })
        
        logger.info("Validated %d of %d detected ambiguities", len(validated), len(ambiguities))
        return validated
