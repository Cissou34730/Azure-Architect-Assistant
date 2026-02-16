"""
Unified AI Service
Single entry point for all AI operations (LLM and Embeddings).
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any

from .config import AIConfig
from .interfaces import ChatMessage, EmbeddingProvider, LLMProvider, LLMResponse
from .providers import OpenAIEmbeddingProvider, OpenAILLMProvider

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
        self.config = config or AIConfig()
        self.config.validate_provider_config()

        self._llm_provider = self._create_llm_provider()
        self._embedding_provider = self._create_embedding_provider()

        logger.info(
            f"AIService initialized - LLM: {self.config.llm_provider}, "
            f"Embedding: {self.config.embedding_provider}"
        )

    def _create_llm_provider(self) -> LLMProvider:
        """Factory method to create LLM provider based on config."""
        if self.config.llm_provider == "openai":
            return OpenAILLMProvider(self.config)
        elif self.config.llm_provider == "azure":
            # TODO: Implement AzureOpenAILLMProvider
            raise NotImplementedError("Azure OpenAI LLM provider not yet implemented")
        elif self.config.llm_provider == "anthropic":
            # TODO: Implement AnthropicLLMProvider
            raise NotImplementedError("Anthropic LLM provider not yet implemented")
        else:
            raise ValueError(f"Unknown LLM provider: {self.config.llm_provider}")

    def _create_embedding_provider(self) -> EmbeddingProvider:
        """Factory method to create embedding provider based on config."""
        if self.config.embedding_provider == "openai":
            return OpenAIEmbeddingProvider(self.config)
        elif self.config.embedding_provider == "azure":
            # TODO: Implement AzureOpenAIEmbeddingProvider
            raise NotImplementedError(
                "Azure OpenAI embedding provider not yet implemented"
            )
        else:
            raise ValueError(
                f"Unknown embedding provider: {self.config.embedding_provider}"
            )

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
            messages = [
                ChatMessage(role=m["role"], content=m["content"]) for m in messages
            ]

        temp = (
            temperature if temperature is not None else self.config.default_temperature
        )
        tokens = (
            max_tokens if max_tokens is not None else self.config.default_max_tokens
        )

        return await self._llm_provider.chat(
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

        return await self._llm_provider.complete(
            prompt=prompt, temperature=temp, max_tokens=tokens, **kwargs
        )

    def get_llm_model(self) -> str:
        """Get current LLM model name."""
        return self._llm_provider.get_model_name()

    def create_chat_llm(self, **overrides) -> Any:
        """
        Create a LangChain-compatible chat LLM instance (ChatOpenAI) using
        the current configuration. Caller may override parameters.

        Returns a provider-specific LLM object (e.g., ChatOpenAI) ready to
        be passed into agent/tool constructors.
        """
        # Lazy import to avoid hard dependency at module import time
        try:
            from langchain_openai import ChatOpenAI  # noqa: PLC0415
        except Exception as err:
            # If LangChain's ChatOpenAI isn't available, raise a clear error.
            raise RuntimeError("ChatOpenAI (langchain_openai) is required to create a chat LLM") from err

        params = {
            "model": getattr(self.config, "openai_llm_model", None),
            "temperature": getattr(self.config, "default_temperature", 0.1),
            "openai_api_key": getattr(self.config, "openai_api_key", None),
        }
        params.update(overrides)
        return ChatOpenAI(**{k: v for k, v in params.items() if v is not None})

    # ============ Embedding Methods ============

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for single text.

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        return await self._embedding_provider.embed_text(text)

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
        return await self._embedding_provider.embed_batch(texts, batch_size)

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

    @classmethod
    def get_instance(cls, config: AIConfig | None = None) -> "AIService":
        """Get or create AIService singleton."""
        if cls._instance is None:
            cls._instance = AIService(config)
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "AIService | None") -> None:
        """Set or clear singleton instance (for testing/lifecycle)."""
        cls._instance = instance

    @classmethod
    async def reinitialize_with_model(cls, new_model: str) -> None:
        """
        Reinitialize AIService with a new model.
        
        Thread-safe implementation using asyncio.Lock to prevent concurrent
        reinitializations. Waits for in-flight requests via a grace period.
        Clears all cached service instances to ensure fresh initialization.
        
        Args:
            new_model: New model ID to use (e.g., "gpt-4-turbo-preview")
        
        Raises:
            ValueError: If model ID is invalid or reinitialization fails
        """
        async with cls._lock:
            logger.info(f"Reinitialization requested: changing model to {new_model}")
            
            # Get current instance (if any)
            old_instance = cls._instance
            old_model = old_instance.get_llm_model() if old_instance else None
            
            if old_model == new_model:
                logger.info(f"Model already set to {new_model}, skipping reinitialization")
                return
            
            # Grace period for in-flight requests (simple approach)
            # More sophisticated: maintain request counter and wait for zero
            await asyncio.sleep(0.5)
            
            try:
                # Create new config with updated model
                new_config = AIConfig(openai_llm_model=new_model)
                new_config.validate_provider_config()
                
                # Create new AIService instance
                new_instance = AIService(new_config)
                
                # Replace singleton instance
                cls._instance = new_instance
                
                # CRITICAL: Clear all cached service instances that depend on AIService
                # This ensures fresh instances are created with the new model
                get_ai_service.cache_clear()
                logger.debug("Cleared get_ai_service LRU cache")
                
                # Clear LLMService singleton to force recreation with new AI service
                from app.services.llm_service import LLMServiceSingleton  # noqa: PLC0415
                LLMServiceSingleton.set_instance(None)
                logger.debug("Cleared LLMService singleton instance")
                
                logger.info(
                    f"AIService reinitialized: {old_model} -> {new_model} "
                    f"(all service caches cleared)"
                )
                
            except Exception as e:
                logger.error(f"Failed to reinitialize AIService with model {new_model}: {e}")
                # Keep old instance if reinitialization fails
                if old_instance:
                    cls._instance = old_instance
                raise ValueError(f"Failed to change model to {new_model}: {e!s}") from e


@lru_cache(maxsize=1)
def get_ai_service(config: AIConfig | None = None) -> AIService:
    """
    Get or create AIService singleton.

    Args:
        config: Optional configuration (only used on first call)

    Returns:
        AIService instance
    """
    return AIServiceManager.get_instance(config)

