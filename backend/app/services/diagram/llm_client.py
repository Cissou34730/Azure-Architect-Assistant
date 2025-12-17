"""Diagram-specific OpenAI LLM client with retry logic and rate limiting."""

import asyncio
from typing import Optional, Dict, Any
import logging

from openai import AsyncOpenAI, APIError, RateLimitError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import get_app_settings, get_openai_settings

logger = logging.getLogger(__name__)


class DiagramLLMClient:
    """
    Diagram-specific LLM client with diagram generation optimizations.
    
    Features:
    - Automatic retry with exponential backoff
    - Rate limiting compliance
    - Diagram-specific prompt handling
    - Separate from general llm_service.py for isolation
    """
    
    def __init__(self):
        """Initialize diagram LLM client with settings."""
        app_settings = get_app_settings()
        openai_settings = get_openai_settings()
        
        self.client = AsyncOpenAI(api_key=openai_settings.api_key)
        self.model = app_settings.diagram_openai_model
        self.max_retries = app_settings.diagram_max_retries
        self.timeout = app_settings.diagram_generation_timeout
        
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
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at generating architecture diagrams from text descriptions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout,
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("LLM returned empty response")
                
            return content.strip()
            
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
    ) -> Dict[str, Any]:
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
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at validating architecture diagrams. Return JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=1000,
                timeout=10,
                response_format={"type": "json_object"},
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("LLM returned empty validation response")
            
            import json
            return json.loads(content)
            
        except APIError as e:
            logger.error(f"Semantic validation API error: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in validation response: {e}")
            raise ValueError(f"LLM returned invalid JSON: {e}")
            
    async def detect_ambiguities(
        self,
        description: str,
        temperature: float = 0.4,
    ) -> Dict[str, Any]:
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
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at identifying unclear requirements. Return JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=2000,
                timeout=15,
                response_format={"type": "json_object"},
            )
            
            content = response.choices[0].message.content
            if not content:
                return {"ambiguities": []}
            
            import json
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Ambiguity detection error: {e}")
            return {"ambiguities": []}  # Non-fatal, return empty list
