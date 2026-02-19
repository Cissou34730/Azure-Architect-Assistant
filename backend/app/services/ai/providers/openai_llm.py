"""
OpenAI LLM Provider Implementation
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI, BadRequestError

from ..config import AIConfig
from ..interfaces import ChatMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OpenAILLMProvider(LLMProvider):
    """
    OpenAI implementation of LLM provider.

    Uses OpenAI Responses API as the single inference interface to support
    modern model families consistently.
    """

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

    def _to_response_input(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        """Convert internal chat messages to OpenAI Responses API input format."""
        return [
            {
                "role": msg.role,
                "content": [{"type": "input_text", "text": msg.content}],
            }
            for msg in messages
        ]

    def _build_responses_params(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        include_temperature: bool = True,
        include_text_format: bool = True,
        stream: bool = False,
        **kwargs,
    ) -> dict[str, Any]:
        """Build parameters for the OpenAI Responses API call."""
        params: dict[str, Any] = {
            "model": self.model,
            "input": self._to_response_input(messages),
            "max_output_tokens": max_tokens,
        }

        if include_temperature:
            params["temperature"] = temperature

        response_format = kwargs.pop("response_format", None)
        if include_text_format and isinstance(response_format, dict):
            format_type = response_format.get("type")
            if format_type == "json_object":
                params["text"] = {"format": {"type": "json_object"}}

        if stream:
            params["stream"] = True

        params.update(kwargs)
        return params

    def _build_attempts(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        stream: bool,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """Build a deterministic sequence of compatible parameter attempts."""
        return [
            self._build_responses_params(
                messages,
                temperature,
                max_tokens,
                include_temperature=True,
                include_text_format=True,
                stream=stream,
                **kwargs,
            ),
            self._build_responses_params(
                messages,
                temperature,
                max_tokens,
                include_temperature=False,
                include_text_format=True,
                stream=stream,
                **kwargs,
            ),
            self._build_responses_params(
                messages,
                temperature,
                max_tokens,
                include_temperature=False,
                include_text_format=False,
                stream=stream,
                **kwargs,
            ),
        ]

    def _extract_response_text(self, response: Any) -> str:
        """Extract response text from Responses API result."""
        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text

        outputs = getattr(response, "output", None)
        if not outputs:
            return ""

        text_fragments: list[str] = []
        for item in outputs:
            content_items = getattr(item, "content", None) or []
            for content in content_items:
                text_value = getattr(content, "text", None)
                if isinstance(text_value, str):
                    text_fragments.append(text_value)
                    continue

                if text_value is not None:
                    maybe_value = getattr(text_value, "value", None)
                    if isinstance(maybe_value, str):
                        text_fragments.append(maybe_value)

                maybe_value = getattr(content, "value", None)
                if isinstance(maybe_value, str):
                    text_fragments.append(maybe_value)

        return "".join(text_fragments)

    @staticmethod
    def _extract_usage(response: Any) -> dict[str, int] | None:
        """Extract usage fields from Responses API result if available."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return None

        prompt_tokens = getattr(usage, "input_tokens", None)
        completion_tokens = getattr(usage, "output_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)

        if (
            isinstance(prompt_tokens, int)
            and isinstance(completion_tokens, int)
            and isinstance(total_tokens, int)
        ):
            return {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }

        return None

    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        **kwargs,
    ) -> LLMResponse | AsyncIterator[str]:
        """
        Generate chat completion using OpenAI.

        Automatically adapts to model requirements by handling API errors
        and retrying with compatible parameters.
        """
        try:
            if stream:
                return self._stream_chat(messages, temperature, max_tokens, **kwargs)

            attempts = self._build_attempts(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                **kwargs,
            )

            last_error: Exception | None = None
            for index, params in enumerate(attempts, start=1):
                try:
                    response = await self.client.responses.create(**params)
                    content = self._extract_response_text(response)

                    return LLMResponse(
                        content=content,
                        model=getattr(response, "model", self.model),
                        usage=self._extract_usage(response),
                        finish_reason=None,
                    )
                except BadRequestError as bad_request_error:
                    last_error = bad_request_error
                    logger.warning(
                        "Responses API attempt %s/3 failed for model %s: %s",
                        index,
                        self.model,
                        bad_request_error,
                    )
                    continue

            if last_error is not None:
                raise last_error
            raise RuntimeError("Responses API failed without explicit error")

        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            raise

    async def _stream_chat(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream chat completion via Responses API server-sent events."""
        try:
            attempts = self._build_attempts(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )

            last_error: Exception | None = None
            for index, params in enumerate(attempts, start=1):
                try:
                    stream = await self.client.responses.create(**params)
                    async for event in stream:
                        event_type = getattr(event, "type", "")
                        if event_type == "response.output_text.delta":
                            delta = getattr(event, "delta", None)
                            if isinstance(delta, str) and delta:
                                yield delta
                    return
                except BadRequestError as bad_request_error:
                    last_error = bad_request_error
                    logger.warning(
                        "Responses stream attempt %s/3 failed for model %s: %s",
                        index,
                        self.model,
                        bad_request_error,
                    )
                    continue

            # Final fallback: non-stream response emitted as a single chunk
            if last_error is not None:
                logger.warning(
                    "Streaming unavailable for model %s, falling back to non-stream response",
                    self.model,
                )
                response = await self.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                    **kwargs,
                )
                if isinstance(response, LLMResponse) and response.content:
                    yield response.content
                return

            raise RuntimeError("Responses stream failed without explicit error")

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

