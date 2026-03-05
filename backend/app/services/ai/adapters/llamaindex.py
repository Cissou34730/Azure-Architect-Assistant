"""
LlamaIndex Adapters for AIService

Provides LlamaIndex-compatible interfaces that delegate to the unified AIService.
This allows LlamaIndex code to continue working unchanged while using centralized
AI service configuration and monitoring.

Note on event-loop bridging
---------------------------
LlamaIndex's synchronous ``_get_*_embedding`` and ``complete``/``chat`` methods
must call async AIService methods from a (potentially) already-running event loop.
``nest_asyncio.apply()`` is called **once at module load time** to allow
``loop.run_until_complete()`` to be called from within a running loop.

This is a process-wide side effect.  Callers that require strict asyncio
isolation should use the async ``_aget_*`` methods directly instead of
relying on these sync shims.
"""

import asyncio
import logging
from typing import Any, ClassVar, cast

import nest_asyncio
from llama_index.core.base.llms.types import (
    ChatMessage as LlamaIndexChatMessage,
)
from llama_index.core.base.llms.types import (
    ChatResponse,
    ChatResponseGen,
    CompletionResponse,
    CompletionResponseGen,
    LLMMetadata,
    MessageRole,
)
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms import CustomLLM

from ..ai_service import AIService
from ..interfaces import ChatMessage, LLMResponse

logger = logging.getLogger(__name__)

# Apply nest_asyncio once at module load time so sync adapter methods can safely
# call run_until_complete even when an event loop is already running.
nest_asyncio.apply()


def _run_async(coro: Any) -> Any:
    """Execute a coroutine synchronously.

    Prefers the already-running event loop (nest_asyncio makes run_until_complete
    safe in that case).  Falls back to a fresh event loop when no loop is
    running, closing it afterwards to avoid resource leaks.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop – spin up a temporary one.
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    return loop.run_until_complete(coro)


class AIServiceLLM(CustomLLM):
    """
    LlamaIndex-compatible LLM that delegates to AIService.

    This adapter allows LlamaIndex to use the unified AIService while
    maintaining full compatibility with LlamaIndex's LLM interface.
    """

    ai_service: AIService
    model_name: str
    temperature: float
    max_tokens: int

    model_config: ClassVar[dict[str, Any]] = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        ai_service: AIService,
        model_name: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ):
        """
        Initialize LlamaIndex adapter for AIService.

        Args:
            ai_service: The unified AIService instance
            model_name: Override model name (uses config default if not provided)
            temperature: Temperature for generation (uses config default if not provided)
            max_tokens: Maximum tokens to generate (uses config default if not provided)
        """
        super().__init__(
            ai_service=ai_service,
            model_name=model_name or ai_service.config.openai_llm_model,
            temperature=temperature
            if temperature is not None
            else ai_service.config.default_temperature,
            max_tokens=max_tokens
            if max_tokens is not None
            else ai_service.config.default_max_tokens,
            **kwargs,
        )
        logger.info("AIServiceLLM adapter initialized: model=%s", self.model_name)

    @property
    def metadata(self) -> LLMMetadata:
        """LLM metadata required by LlamaIndex."""
        return LLMMetadata(
            model_name=self.model_name,
            num_output=self.max_tokens,
            is_chat_model=True,
        )

    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """
        Synchronous completion call (required by LlamaIndex).

        Args:
            prompt: Text prompt for completion
            **kwargs: Additional parameters

        Returns:
            CompletionResponse with generated text
        """
        response = _run_async(
            self.ai_service.complete(
                prompt,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
            )
        )
        return CompletionResponse(text=response)

    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        """Streaming not implemented for adapter."""
        raise NotImplementedError("Streaming not supported in adapter")

    def chat(
        self, messages: list[LlamaIndexChatMessage], **kwargs: Any
    ) -> ChatResponse:
        """
        Chat completion (required by LlamaIndex).

        Args:
            messages: List of chat messages
            **kwargs: Additional parameters

        Returns:
            ChatResponse with assistant message
        """
        # Convert LlamaIndex messages to AIService format
        ai_messages = [
            ChatMessage(role=msg.role.value, content=msg.content or "")
            for msg in messages
        ]

        response = cast(
            LLMResponse,
            _run_async(
                self.ai_service.chat(
                    ai_messages,
                    temperature=kwargs.get("temperature", self.temperature),
                    max_tokens=kwargs.get("max_tokens", self.max_tokens),
                )
            ),
        )

        return ChatResponse(
            message=LlamaIndexChatMessage(
                role=MessageRole.ASSISTANT, content=response.content
            ),
            raw={"model": response.model, "usage": response.usage},
        )

    def stream_chat(
        self, messages: list[LlamaIndexChatMessage], **kwargs: Any
    ) -> ChatResponseGen:
        """Streaming not implemented for adapter."""
        raise NotImplementedError("Streaming not supported in adapter")


class AIServiceEmbedding(BaseEmbedding):
    """
    LlamaIndex-compatible embedding model that delegates to AIService.

    This adapter allows LlamaIndex to use the unified AIService for embeddings
    while maintaining full compatibility with LlamaIndex's embedding interface.
    """

    ai_service: AIService
    model_name: str

    model_config: ClassVar[dict[str, Any]] = {"arbitrary_types_allowed": True}

    def __init__(
        self, ai_service: AIService, model_name: str | None = None, **kwargs: Any
    ):
        """
        Initialize LlamaIndex adapter for AIService embeddings.

        Args:
            ai_service: The unified AIService instance
            model_name: Override model name (uses config default if not provided)
        """
        super().__init__(
            ai_service=ai_service,
            model_name=model_name or ai_service.config.openai_embedding_model,
            **kwargs,
        )
        logger.info("AIServiceEmbedding adapter initialized: model=%s", self.model_name)

    @classmethod
    def class_name(cls) -> str:
        """Class name for serialization."""
        return "AIServiceEmbedding"

    def _sync_embed(self, text: str) -> list[float]:
        """Bridge async embed_text to sync context."""
        return _run_async(self.ai_service.embed_text(text))

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._sync_embed(query)

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._sync_embed(text)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        """Async get query embedding."""
        return await self.ai_service.embed_text(query)

    async def _aget_text_embedding(self, text: str) -> list[float]:
        """Async get text embedding."""
        return await self.ai_service.embed_text(text)

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Get embeddings for multiple texts (batch).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return _run_async(self.ai_service.embed_batch(texts))

