"""
OpenAI LLM Provider Implementation

Uses Chat Completions by default and automatically falls back to Responses API
when a model is not compatible with chat completions.
"""

import logging
from collections.abc import AsyncIterator
from typing import Any, ClassVar

from openai import APITimeoutError, BadRequestError, NotFoundError

from ..config import AIConfig
from ..interfaces import ChatMessage, LLMProvider, LLMResponse
from .openai_client import get_openai_client

logger = logging.getLogger(__name__)


class OpenAILLMProvider(LLMProvider):
    """OpenAI implementation of LLM provider using Chat Completions API."""
    _preferred_api_by_model: ClassVar[dict[str, str]] = {}

    def __init__(self, config: AIConfig):
        self.config = config
        self.client = get_openai_client(config)
        self.model = config.openai_llm_model
        logger.info("OpenAI LLM Provider initialized with model: %s", self.model)

    @classmethod
    def _set_preferred_api(cls, model: str, api: str) -> None:
        if api not in {"chat", "responses"}:
            return
        cls._preferred_api_by_model[model] = api

    def _ordered_apis(self) -> list[str]:
        preferred = self._preferred_api_by_model.get(self.model)
        if preferred == "responses":
            return ["responses", "chat"]
        if preferred == "chat":
            return ["chat", "responses"]
        return ["chat", "responses"]

    @staticmethod
    def _to_messages(messages: list[ChatMessage]) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in messages]

    @staticmethod
    def _to_response_input(messages: list[ChatMessage]) -> list[dict[str, Any]]:
        return [
            {
                "role": message.role,
                "content": [{"type": "input_text", "text": message.content}],
            }
            for message in messages
        ]

    @staticmethod
    def _extract_usage(response: Any) -> dict[str, int] | None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return None
        pt = getattr(usage, "prompt_tokens", None)
        ct = getattr(usage, "completion_tokens", None)
        tt = getattr(usage, "total_tokens", None)
        if not isinstance(pt, int):
            pt = getattr(usage, "input_tokens", None)
        if not isinstance(ct, int):
            ct = getattr(usage, "output_tokens", None)
        if isinstance(pt, int) and isinstance(ct, int) and isinstance(tt, int):
            return {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": tt}
        return None

    def _build_params(  # noqa: PLR0913
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        token_limit_param: str = "max_tokens",  # noqa: S107
        include_temperature: bool = True,
        response_format: dict | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": self.model,
            "messages": self._to_messages(messages),
            token_limit_param: max_tokens,
        }
        if include_temperature:
            params["temperature"] = temperature
        if isinstance(response_format, dict):
            params["response_format"] = response_format
        return params

    @staticmethod
    def _requires_max_completion_tokens(error: BadRequestError) -> bool:
        """Return True when API indicates max_tokens is unsupported for the model."""
        message = str(error).lower()
        return "max_tokens" in message and "max_completion_tokens" in message

    @staticmethod
    def _is_not_chat_model_error(error: Exception) -> bool:
        """Detect endpoint mismatch when model cannot be used with chat completions."""
        message = str(error).lower()
        return (
            "not a chat model" in message
            or "chat/completions endpoint" in message
            or "v1/chat/completions" in message
        )

    def _build_responses_params(  # noqa: PLR0913
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        include_temperature: bool = True,
        include_text_format: bool = True,
        stream: bool = False,
        response_format: dict | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": self.model,
            "input": self._to_response_input(messages),
            "max_output_tokens": max_tokens,
        }

        if include_temperature:
            params["temperature"] = temperature

        if include_text_format and isinstance(response_format, dict):
            format_type = response_format.get("type")
            if format_type == "json_object":
                params["text"] = {"format": {"type": "json_object"}}

        if stream:
            params["stream"] = True

        return params

    async def _chat_via_chat_completions(
        self,
        client: Any,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        response_format: dict | None,
    ) -> LLMResponse:
        """Run inference via chat completions with compatibility fallbacks."""
        last_error: Exception | None = None
        token_limit_param = "max_tokens"  # noqa: S105

        for compatibility_pass in range(2):
            attempts: list[dict[str, Any]] = [
                self._build_params(
                    messages,
                    temperature,
                    max_tokens,
                    token_limit_param=token_limit_param,
                    include_temperature=True,
                    response_format=response_format,
                ),
                self._build_params(
                    messages,
                    temperature,
                    max_tokens,
                    token_limit_param=token_limit_param,
                    include_temperature=False,
                    response_format=response_format,
                ),
                self._build_params(
                    messages,
                    temperature,
                    max_tokens,
                    token_limit_param=token_limit_param,
                    include_temperature=False,
                    response_format=None,
                ),
            ]

            should_retry_with_max_completion_tokens = False
            for index, params in enumerate(attempts, start=1):
                try:
                    response = await client.chat.completions.create(**params)
                    content = response.choices[0].message.content or ""
                    return LLMResponse(
                        content=content,
                        model=getattr(response, "model", self.model),
                        usage=self._extract_usage(response),
                        finish_reason=response.choices[0].finish_reason,
                    )
                except BadRequestError as error:
                    last_error = error
                    if (
                        token_limit_param == "max_tokens"  # noqa: S105
                        and self._requires_max_completion_tokens(error)
                    ):
                        logger.info(
                            "Model %s requires max_completion_tokens; retrying with compatible token parameter",
                            self.model,
                        )
                        should_retry_with_max_completion_tokens = True
                        break

                    logger.warning(
                        "Chat completions attempt %s/3 failed for model %s: %s",
                        index,
                        self.model,
                        error,
                    )
                    continue

            if should_retry_with_max_completion_tokens and compatibility_pass == 0:
                token_limit_param = "max_completion_tokens"  # noqa: S105
                continue

            break

        if last_error is not None:
            raise last_error
        raise RuntimeError("Chat completions failed without explicit error")

    async def _chat_via_responses(
        self,
        client: Any,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        response_format: dict | None,
    ) -> LLMResponse:
        """Run inference via Responses API with compatibility fallbacks."""
        attempts: list[dict[str, Any]] = [
            self._build_responses_params(
                messages,
                temperature,
                max_tokens,
                include_temperature=True,
                include_text_format=True,
                response_format=response_format,
            ),
            self._build_responses_params(
                messages,
                temperature,
                max_tokens,
                include_temperature=False,
                include_text_format=True,
                response_format=response_format,
            ),
            self._build_responses_params(
                messages,
                temperature,
                max_tokens,
                include_temperature=False,
                include_text_format=False,
                response_format=response_format,
            ),
        ]

        last_error: Exception | None = None
        for index, params in enumerate(attempts, start=1):
            try:
                response = await client.responses.create(**params)
                content = getattr(response, "output_text", None) or ""
                return LLMResponse(
                    content=content,
                    model=getattr(response, "model", self.model),
                    usage=self._extract_usage(response),
                    finish_reason=None,
                )
            except BadRequestError as error:
                last_error = error
                logger.warning(
                    "Responses attempt %s/3 failed for model %s: %s",
                    index,
                    self.model,
                    error,
                )
                continue

        if last_error is not None:
            raise last_error
        raise RuntimeError("Responses API failed without explicit error")

    async def chat(  # noqa: C901, PLR0912
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        **kwargs,
    ) -> LLMResponse | AsyncIterator[str]:
        """Generate chat completion using Chat Completions API."""
        if stream:
            return self._stream_chat(messages, temperature, max_tokens, **kwargs)

        request_timeout = kwargs.pop("timeout", None)
        if isinstance(request_timeout, (int, float)):
            client = self.client.with_options(timeout=float(request_timeout))
        else:
            client = self.client

        response_format: dict | None = kwargs.pop("response_format", None)

        try:
            ordered_apis = self._ordered_apis()
            last_error: Exception | None = None

            for api in ordered_apis:
                try:
                    if api == "chat":
                        response = await self._chat_via_chat_completions(
                            client,
                            messages,
                            temperature,
                            max_tokens,
                            response_format,
                        )
                        self._set_preferred_api(self.model, "chat")
                        return response

                    response = await self._chat_via_responses(
                        client,
                        messages,
                        temperature,
                        max_tokens,
                        response_format,
                    )
                    self._set_preferred_api(self.model, "responses")
                    return response

                except APITimeoutError as timeout_error:
                    last_error = timeout_error
                    logger.warning(
                        "%s API timed out for model %s; trying alternate API",
                        api,
                        self.model,
                    )
                    continue
                except (NotFoundError, BadRequestError) as endpoint_error:
                    last_error = endpoint_error
                    if api == "chat" and self._is_not_chat_model_error(endpoint_error):
                        logger.info(
                            "Model %s is not usable with chat completions; trying Responses API",
                            self.model,
                        )
                        self._set_preferred_api(self.model, "responses")
                        continue
                    if api == "responses" and self._is_not_chat_model_error(endpoint_error):
                        logger.info(
                            "Model %s is not usable with Responses API; trying chat completions",
                            self.model,
                        )
                        self._set_preferred_api(self.model, "chat")
                        continue
                    continue

            if last_error is not None:
                raise last_error
            raise RuntimeError("OpenAI inference failed without explicit error")

        except Exception as e:
            logger.error("OpenAI chat error: %s", e)
            raise

    async def _stream_chat(  # noqa: C901, PLR0912
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream chat completion via Chat Completions API."""
        request_timeout = kwargs.pop("timeout", None)
        if isinstance(request_timeout, (int, float)):
            client = self.client.with_options(timeout=float(request_timeout))
        else:
            client = self.client

        response_format: dict | None = kwargs.pop("response_format", None)
        try:
            token_limit_param = "max_tokens"  # noqa: S105
            for compatibility_pass in range(2):
                params = self._build_params(
                    messages,
                    temperature,
                    max_tokens,
                    token_limit_param=token_limit_param,
                    include_temperature=True,
                    response_format=response_format,
                )
                params["stream"] = True

                try:
                    stream = await client.chat.completions.create(**params)
                    async for chunk in stream:
                        delta = chunk.choices[0].delta.content if chunk.choices else None
                        if delta:
                            yield delta
                    return
                except (NotFoundError, BadRequestError) as error:
                    if (
                        token_limit_param == "max_tokens"  # noqa: S105
                        and isinstance(error, BadRequestError)
                        and self._requires_max_completion_tokens(error)
                        and compatibility_pass == 0
                    ):
                        logger.info(
                            "Model %s requires max_completion_tokens for streaming; retrying with compatible token parameter",
                            self.model,
                        )
                        token_limit_param = "max_completion_tokens"  # noqa: S105
                        continue

                    if self._is_not_chat_model_error(error):
                        logger.info(
                            "Model %s is not usable with chat completions for streaming; falling back to Responses API",
                            self.model,
                        )
                        response_params = self._build_responses_params(
                            messages,
                            temperature,
                            max_tokens,
                            include_temperature=True,
                            include_text_format=True,
                            stream=True,
                            response_format=response_format,
                        )
                        try:
                            stream = await client.responses.create(**response_params)
                        except BadRequestError:
                            response_params.pop("temperature", None)
                            stream = await client.responses.create(**response_params)

                        async for event in stream:
                            event_type = getattr(event, "type", "")
                            if event_type == "response.output_text.delta":
                                delta = getattr(event, "delta", None)
                                if isinstance(delta, str) and delta:
                                    yield delta
                        return

                    # Retry without temperature for reasoning models
                    params.pop("temperature", None)
                    stream = await client.chat.completions.create(**params)
                    async for chunk in stream:
                        delta = chunk.choices[0].delta.content if chunk.choices else None
                        if delta:
                            yield delta
                    return
        except Exception as e:
            logger.error("OpenAI stream error: %s", e)
            raise

    async def complete(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 1000, **kwargs
    ) -> str:
        messages = [ChatMessage(role="user", content=prompt)]
        kwargs.pop("stream", None)  # complete() is always non-streaming
        response = await self.chat(messages, temperature, max_tokens, stream=False, **kwargs)
        if not isinstance(response, LLMResponse):
            raise TypeError(f"Expected LLMResponse from non-streaming chat, got {type(response)}")
        return response.content

    def get_model_name(self) -> str:
        return self.model

    async def list_runtime_models(self) -> list[dict[str, str]]:
        """List runtime-selectable OpenAI model identities."""
        response = await self.client.models.list()
        all_models = list(response.data)

        # Exclude families never used for chat completions.
        excluded_prefixes = (
            "text-embedding",
            "text-similarity",
            "text-search",
            "whisper",
            "dall-e",
            "tts",
            "text-davinci-edit",
            "text-moderation",
            "davinci-",
            "curie-",
            "babbage-",
            "ada-",
        )

        runtime_models = [
            {"id": model.id, "model": model.id}
            for model in all_models
            if not model.id.startswith(excluded_prefixes)
        ]
        runtime_models.sort(key=lambda item: item["id"])
        return runtime_models

