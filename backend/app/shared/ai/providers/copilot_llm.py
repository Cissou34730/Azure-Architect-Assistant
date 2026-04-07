"""GitHub Copilot SDK-backed LLM provider."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from ..config import AIConfig
from ..interfaces import ChatMessage, LLMProvider, LLMResponse
from .copilot_runtime import get_copilot_runtime

logger = logging.getLogger(__name__)


def _split_messages(messages: list[ChatMessage]) -> tuple[str | None, str]:
    system_parts: list[str] = []
    prompt_parts: list[str] = []
    for message in messages:
        if message.role == "system":
            system_parts.append(message.content)
            continue
        prompt_parts.append(f"{message.role.upper()}: {message.content}")
    return ("\n\n".join(system_parts) or None, "\n\n".join(prompt_parts))


class CopilotLLMProvider(LLMProvider):
    """Copilot implementation of the LLM provider using the Python Copilot SDK."""

    def __init__(self, config: AIConfig):
        self.config = config
        self.model = config.copilot_default_model

    async def _chat_once(
        self,
        messages: list[ChatMessage],
        _temperature: float,
        _max_tokens: int,
        **_kwargs: Any,
    ) -> LLMResponse:
        system_message, prompt = _split_messages(messages)
        runtime = await get_copilot_runtime(self.config)
        content = await runtime.send_message(
            prompt=prompt,
            model=self.model,
            system_message=system_message,
            timeout=self.config.copilot_request_timeout,
        )
        return LLMResponse(content=content, model=self.model, usage=None, finish_reason="stop")

    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        **kwargs: Any,
    ) -> LLMResponse | AsyncIterator[str]:
        if stream:
            response = await self._chat_once(messages, temperature, max_tokens, **kwargs)

            async def _single_chunk() -> AsyncIterator[str]:
                if response.content:
                    yield response.content

            return _single_chunk()

        return await self._chat_once(messages, temperature, max_tokens, **kwargs)

    async def complete(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 1000, **kwargs: Any
    ) -> str:
        response = await self.chat(
            [ChatMessage(role="user", content=prompt)],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            **kwargs,
        )
        if not isinstance(response, LLMResponse):
            raise TypeError(f"Expected LLMResponse from non-streaming chat, got {type(response)}")
        return response.content

    def get_model_name(self) -> str:
        return self.model

    async def list_runtime_models(self) -> list[dict[str, Any]]:
        try:
            runtime = await get_copilot_runtime(self.config)
            sdk_models = await runtime.list_models()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Copilot SDK model discovery failed, falling back to configured allowlist: %s",
                exc,
            )
            return self._fallback_model_list()

        if not sdk_models:
            return self._fallback_model_list()

        result: list[dict[str, str]] = []
        for m in sdk_models:
            model_id = m.id.lstrip("/")
            friendly = getattr(m, "name", model_id) or model_id
            result.append({"id": model_id, "model": model_id, "name": friendly})

        result.sort(key=lambda item: item["id"])
        return result

    def _fallback_model_list(self) -> list[dict[str, str]]:
        """Return configured allowlist models when catalog is unavailable."""
        allowed = [
            item.strip()
            for item in self.config.copilot_allowed_models.split(",")
            if item.strip()
        ]
        if self.model and self.model not in allowed:
            allowed.insert(0, self.model)
        return [{"id": item, "model": item, "name": item} for item in allowed]
