"""
OpenAI LLM Provider Implementation
"""

import logging
from typing import List, AsyncIterator
from openai import AsyncOpenAI

from ..interfaces import LLMProvider, ChatMessage, LLMResponse
from ..config import AIConfig

logger = logging.getLogger(__name__)


class OpenAILLMProvider(LLMProvider):
    """OpenAI implementation of LLM provider."""

    def __init__(self, config: AIConfig):
        """
        Initialize OpenAI LLM provider.

        Args:
            config: AI configuration
        """
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.openai_api_key,
            timeout=config.openai_timeout,
            max_retries=config.openai_max_retries,
        )
        self.model = config.openai_llm_model
        logger.info(f"OpenAI LLM Provider initialized with model: {self.model}")

    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        **kwargs,
    ) -> LLMResponse | AsyncIterator[str]:
        """Generate chat completion using OpenAI."""
        # Convert messages to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        try:
            if stream:
                return self._stream_chat(
                    openai_messages, temperature, max_tokens, **kwargs
                )
            else:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=openai_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )

                return LLMResponse(
                    content=response.choices[0].message.content,
                    model=response.model,
                    usage={
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    }
                    if response.usage
                    else None,
                    finish_reason=response.choices[0].finish_reason,
                )
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            raise

    async def _stream_chat(
        self, messages: List[dict], temperature: float, max_tokens: int, **kwargs
    ) -> AsyncIterator[str]:
        """Stream chat completion."""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI stream error: {e}")
            raise

    async def complete(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 1000, **kwargs
    ) -> str:
        """Simple text completion."""
        messages = [ChatMessage(role="user", content=prompt)]
        response = await self.chat(messages, temperature, max_tokens, **kwargs)
        return response.content

    def get_model_name(self) -> str:
        """Get current model name."""
        return self.model
