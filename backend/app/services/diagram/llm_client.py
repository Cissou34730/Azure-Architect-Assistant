"""Diagram-specific OpenAI LLM client with retry logic and rate limiting."""

import json
import logging
from typing import Any

from openai import APIError, APITimeoutError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.app_settings import get_app_settings
from app.services.ai.ai_service import AIService, AIServiceManager
from app.services.ai.interfaces import ChatMessage

logger = logging.getLogger(__name__)


class DiagramLLMClient:
    """
    Diagram-specific LLM client with diagram generation optimizations.

    Features:
    - Uses centralized AIService for consistent model management
    - Automatic retry with exponential backoff
    - Rate limiting compliance
    - Diagram-specific prompt handling
    """

    def __init__(self, ai_service: AIService | None = None) -> None:
        """
        Initialize diagram LLM client with AIService.
        
        Args:
            ai_service: Optional AIService instance (uses singleton if None)
        """
        app_settings = get_app_settings()

        self.ai_service = ai_service or AIServiceManager.get_instance()
        self.max_retries = app_settings.diagram_max_retries
        self.timeout = app_settings.diagram_generation_timeout

        logger.info(
            f"DiagramLLMClient initialized with model: {self.ai_service.get_llm_model()}"
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
        reraise=True,
    )
    async def generate_diagram(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> str:
        """
        Generate diagram code using LLM.

        Args:
            prompt: System and user prompt for diagram generation
            temperature: Lower temperature for more deterministic output
            max_tokens: Maximum tokens in response

        Returns:
            Generated diagram source code

        Raises:
            APIError: On OpenAI API errors
            RateLimitError: On rate limit (retried automatically)
            APITimeoutError: On timeout (retried automatically)
        """
        try:
            messages = [
                ChatMessage(
                    role="system",
                    content="You are an expert at generating architecture diagrams from text descriptions.",
                ),
                ChatMessage(role="user", content=prompt),
            ]

            response = await self.ai_service.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.content
            if not content:
                raise ValueError("LLM returned empty response")

            # Strip markdown code fences if present
            cleaned_content = self._strip_code_fences(content.strip())
            return cleaned_content

        except RateLimitError as e:
            logger.warning(f"Rate limit hit, retrying: {e}")
            raise
        except APITimeoutError as e:
            logger.warning(f"API timeout, retrying: {e}")
            raise
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def validate_semantics(
        self,
        prompt: str,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """
        Use LLM to validate diagram semantics.

        Args:
            prompt: Validation prompt comparing description to diagram
            temperature: Low temperature for consistent validation

        Returns:
            Parsed validation result as dictionary

        Raises:
            APIError: On OpenAI API errors
            ValueError: If response is not valid JSON
        """
        try:
            messages = [
                ChatMessage(
                    role="system",
                    content="You are an expert at validating architecture diagrams. Return JSON only.",
                ),
                ChatMessage(role="user", content=prompt),
            ]

            # Note: AIService doesn't currently expose response_format parameter
            # We rely on the prompt to request JSON output
            response = await self.ai_service.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=1000,
            )

            content = response.content
            if not content:
                raise ValueError("LLM returned empty validation response")

            return json.loads(content)

        except APIError as e:
            logger.error(f"Semantic validation API error: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in validation response: {e}")
            raise ValueError(f"LLM returned invalid JSON: {e}") from e

    async def detect_ambiguities(
        self,
        description: str,
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        """
        Detect ambiguities in architecture description using LLM.

        Args:
            description: Input architecture description
            temperature: Moderate temperature for ambiguity detection

        Returns:
            Dictionary with ambiguities list

        Raises:
            APIError: On OpenAI API errors
        """
        prompt = f"""Analyze the following architecture description for ambiguous or unclear elements.

Description:
{description}

Return JSON with this structure:
{{
  "ambiguities": [
    {{
      "text": "exact ambiguous text from description",
      "issue": "what makes this unclear",
      "clarification": "suggested clarification question"
    }}
  ]
}}

Focus on:
- Vague component names
- Unclear relationships
- Missing specifications
- Ambiguous requirements
"""

        try:
            messages = [
                ChatMessage(
                    role="system",
                    content="You are an expert at identifying unclear requirements. Return JSON only.",
                ),
                ChatMessage(role="user", content=prompt),
            ]

            response = await self.ai_service.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=2000,
            )

            content = response.content
            if not content:
                return {"ambiguities": []}

            return json.loads(content)

        except (APIError, json.JSONDecodeError) as e:
            logger.error(f"Ambiguity detection error: {e}")
            return {"ambiguities": []}

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        """
        Strip markdown code fences from LLM output.

        Handles:
        - ```mermaid ... ```
        - ```plantuml ... ```
        - ``` ... ```
        - Leading/trailing explanations

        Args:
            content: Raw LLM output

        Returns:
            Cleaned diagram code
        """
        content = content.strip()

        # Remove markdown code fences
        if content.startswith("```"):
            # Find first newline after opening fence
            first_newline: int = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1 :]

            # Remove closing fence
            if content.endswith("```"):
                content = content[:-3]

        return content.strip()

