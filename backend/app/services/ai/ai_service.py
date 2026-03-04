"""
Unified AI Service
Single entry point for all AI operations (LLM and Embeddings).
"""

import asyncio
import logging
import threading
from collections.abc import AsyncIterator
from typing import Any, cast

from .config import AIConfig
from .interfaces import ChatMessage, EmbeddingProvider, LLMProvider, LLMResponse
from .providers import (
    AzureOpenAIEmbeddingProvider,
    AzureOpenAILLMProvider,
    OpenAIEmbeddingProvider,
    OpenAILLMProvider,
    reset_azure_openai_client,
    reset_openai_client,
)
from .router import AIRouter

logger = logging.getLogger(__name__)


class AIService:
    """
    Unified AI service providing access to LLM and Embedding capabilities.
    Abstracts provider details and provides a consistent interface.
    """

    def __init__(self, config: AIConfig | None = None):
        """
        Initialize AI service with configuration.

        Args:
            config: AI configuration (if None, loads from environment)
        """
        self.config = config or AIConfig.default()
        self.config.validate_provider_config()

        self._llm_provider = self._create_llm_provider(self.config.llm_provider)
        self._embedding_provider = self._create_embedding_provider(
            self.config.embedding_provider
        )
        self._fallback_llm_provider = self._create_fallback_llm_provider()
        self._fallback_embedding_provider = self._create_fallback_embedding_provider()
        self._router = AIRouter(
            primary_llm=self._llm_provider,
            primary_embedding=self._embedding_provider,
            fallback_llm=self._fallback_llm_provider,
            fallback_embedding=self._fallback_embedding_provider,
            fallback_enabled=self.config.fallback_enabled,
            fallback_on_transient_only=self.config.fallback_on_transient_only,
        )

        logger.info(
            "AIService initialized - LLM: %s, Embedding: %s, fallback: %s",
            self.config.llm_provider,
            self.config.embedding_provider,
            self.config.fallback_provider if self.config.fallback_enabled else "disabled",
        )

    def _create_llm_provider(self, provider_name: str) -> LLMProvider:
        """Factory method to create LLM provider based on config."""
        if provider_name == "openai":
            return OpenAILLMProvider(self.config)
        elif provider_name == "azure":
            return AzureOpenAILLMProvider(self.config)
        elif provider_name == "anthropic":
            # TODO: Implement AnthropicLLMProvider
            raise NotImplementedError("Anthropic LLM provider not yet implemented")
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")

    def _create_embedding_provider(self, provider_name: str) -> EmbeddingProvider:
        """Factory method to create embedding provider based on config."""
        if provider_name == "openai":
            return OpenAIEmbeddingProvider(self.config)
        elif provider_name == "azure":
            return AzureOpenAIEmbeddingProvider(self.config)
        else:
            raise ValueError(f"Unknown embedding provider: {provider_name}")

    def _create_fallback_llm_provider(self) -> LLMProvider | None:
        if not self.config.fallback_enabled or self.config.fallback_provider == "none":
            return None
        if self.config.fallback_provider == self.config.llm_provider:
            return None
        return self._create_llm_provider(self.config.fallback_provider)

    def _create_fallback_embedding_provider(self) -> EmbeddingProvider | None:
        if not self.config.fallback_enabled or self.config.fallback_provider == "none":
            return None
        if self.config.fallback_provider == self.config.embedding_provider:
            return None
        return self._create_embedding_provider(self.config.fallback_provider)

    # ============ LLM Methods ============

    async def chat(
        self,
        messages: list[ChatMessage] | list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs,
    ) -> LLMResponse | AsyncIterator[str]:
        """
        Generate chat completion.

        Args:
            messages: List of ChatMessage or dicts with 'role' and 'content'
            temperature: Sampling temperature (defaults to config)
            max_tokens: Maximum tokens (defaults to config)
            stream: Whether to stream response
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse or AsyncIterator[str] if streaming
        """
        # Convert dict messages to ChatMessage if needed
        if messages and isinstance(messages[0], dict):
            dict_messages = cast(list[dict[str, Any]], messages)
            messages = [
                ChatMessage(role=m["role"], content=m["content"])
                for m in dict_messages
            ]

        temp = (
            temperature if temperature is not None else self.config.default_temperature
        )
        tokens = (
            max_tokens if max_tokens is not None else self.config.default_max_tokens
        )

        return await self._router.chat(
            messages=messages,
            temperature=temp,
            max_tokens=tokens,
            stream=stream,
            **kwargs,
        )

    async def complete(
        self,
        prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> str:
        """
        Simple text completion.

        Args:
            prompt: Text prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Provider-specific parameters

        Returns:
            Generated text
        """
        temp = (
            temperature if temperature is not None else self.config.default_temperature
        )
        tokens = (
            max_tokens if max_tokens is not None else self.config.default_max_tokens
        )

        return await self._router.complete(
            prompt=prompt, temperature=temp, max_tokens=tokens, **kwargs
        )

    def get_llm_model(self) -> str:
        """Get current LLM model name."""
        return self._llm_provider.get_model_name()

    # ============ Embedding Methods ============

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for single text.

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        return await self._router.embed_text(text)

    async def embed_batch(
        self, texts: list[str], batch_size: int | None = None
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            batch_size: Batch size (defaults to 100)

        Returns:
            List of embedding vectors
        """
        batch_size = batch_size or 100
        return await self._router.embed_batch(texts, batch_size)

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self._embedding_provider.get_embedding_dimension()

    def get_embedding_model(self) -> str:
        """Get current embedding model name."""
        return self._embedding_provider.get_model_name()


class AIServiceManager:
    """
    Manages the AIService singleton instance.

    SINGLETON RATIONALE:
    - Provider abstraction: Manages OpenAI, Azure OpenAI, Anthropic clients
    - Connection pooling: Shared HTTP clients across requests
    - Model caching: Embedding models loaded once and reused
    - Configuration consistency: All requests use same AI provider settings

    Testability:
    - Override via FastAPI dependency injection (see app.dependencies.get_ai_service_dependency)
    - Use set_instance() to inject mock in unit tests
    - See tests/conftest.py for mock_ai_service fixture
    """

    _instance: "AIService | None" = None
    _lock: asyncio.Lock = asyncio.Lock()
    _init_lock: threading.Lock = threading.Lock()

    @classmethod
    def get_instance(cls, config: AIConfig | None = None) -> "AIService":
        """Get or create AIService singleton (thread-safe via double-checked locking)."""
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = AIService(config)
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "AIService | None") -> None:
        """Set or clear singleton instance (for testing/lifecycle)."""
        cls._instance = instance

    @classmethod
    def create_probe(cls, config: AIConfig) -> "AIService":
        """
        Create a temporary AIService for probing (not registered as singleton).
        Use this when you need to test a configuration without committing it.
        """
        return AIService(config)

    @classmethod
    async def reinitialize_with_model(cls, new_model: str) -> None:
        """
        Reinitialize AIService with a new model.

        Thread-safe implementation using asyncio.Lock to prevent concurrent
        reinitializations. Waits for in-flight requests via a grace period.
        Clears shared HTTP client singletons so new providers connect with
        fresh credentials/configuration.

        Args:
            new_model: New model ID to use (e.g., "gpt-4-turbo-preview")

        Raises:
            ValueError: If model ID is invalid or reinitialization fails

        Note:
            The grace period is a best-effort drain; in-flight requests that
            outlast the sleep will continue on the old instance.
        """
        async with cls._lock:
            logger.info("Reinitialization requested: changing model to %s", new_model)

            # Get current instance (if any)
            old_instance = cls._instance
            old_model = old_instance.get_llm_model() if old_instance else None

            if old_model == new_model:
                logger.info("Model already set to %s, skipping reinitialization", new_model)
                return

            # Grace period for in-flight requests (best-effort drain)
            from app.core.app_settings import get_app_settings  # noqa: PLC0415
            await asyncio.sleep(get_app_settings().ai_reinit_grace_sleep)

            try:
                # Build new config via immutable model_copy (AIConfig is a frozen BaseModel)
                base_config = AIConfig.default()
                if base_config.llm_provider == "azure":
                    new_config = base_config.model_copy(update={"azure_llm_deployment": new_model})
                else:
                    new_config = base_config.model_copy(update={"openai_llm_model": new_model})
                new_config.validate_provider_config()

                # Reset shared HTTP client singletons so new providers get a fresh client
                reset_openai_client()
                reset_azure_openai_client()

                # Create new AIService instance
                new_instance = AIService(new_config)

                # Replace singleton instance
                cls._instance = new_instance

                # Notify dependent services to refresh their cached AI service reference
                cls._notify_dependents()

                logger.info(
                    "AIService reinitialized: %s -> %s",
                    old_model,
                    new_model,
                )

            except Exception as e:
                logger.error("Failed to reinitialize AIService with model %s: %s", new_model, e)
                # Keep old instance if reinitialization fails
                if old_instance:
                    cls._instance = old_instance
                raise ValueError(f"Failed to change model to {new_model}: {e!s}") from e

    @classmethod
    def _notify_dependents(cls) -> None:
        """Clear downstream singleton caches that hold a reference to AIService."""
        try:
            from app.services.llm_service import LLMServiceSingleton  # noqa: PLC0415
            LLMServiceSingleton.set_instance(None)
            logger.debug("Cleared LLMService singleton instance")
        except ImportError:
            pass


def get_ai_service(config: AIConfig | None = None) -> AIService:
    """
    Get or create AIService singleton.

    Args:
        config: Optional configuration (only used on first call)

    Returns:
        AIService instance
    """
    return AIServiceManager.get_instance(config)

