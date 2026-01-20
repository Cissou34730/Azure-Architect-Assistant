"""
Unified AI Service
Single entry point for all AI operations (LLM and Embeddings).
"""

import logging
from typing import List, Optional, AsyncIterator, Any
from functools import lru_cache

from .config import AIConfig
from .interfaces import LLMProvider, EmbeddingProvider, ChatMessage, LLMResponse
from .providers import OpenAILLMProvider, OpenAIEmbeddingProvider

logger = logging.getLogger(__name__)


class AIService:
    """
    Unified AI service providing access to LLM and Embedding capabilities.
    Abstracts provider details and provides a consistent interface.
    """

    def __init__(self, config: Optional[AIConfig] = None):
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
        messages: List[ChatMessage] | List[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
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
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
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
            from langchain_openai import ChatOpenAI
        except Exception:
            # If LangChain's ChatOpenAI isn't available, fallback to provider
            # constructs or raise a clear error.
            raise RuntimeError("ChatOpenAI (langchain_openai) is required to create a chat LLM")

        params = {
            "model": getattr(self.config, "openai_llm_model", None),
            "temperature": getattr(self.config, "default_temperature", 0.1),
            "openai_api_key": getattr(self.config, "openai_api_key", None),
        }
        params.update(overrides)
        return ChatOpenAI(**{k: v for k, v in params.items() if v is not None})

    # ============ Embedding Methods ============

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for single text.

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        return await self._embedding_provider.embed_text(text)

    async def embed_batch(
        self, texts: List[str], batch_size: Optional[int] = None
    ) -> List[List[float]]:
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


# Singleton instance
_ai_service: Optional[AIService] = None


@lru_cache(maxsize=1)
def get_ai_service(config: Optional[AIConfig] = None) -> AIService:
    """
    Get or create AIService singleton.

    Args:
        config: Optional configuration (only used on first call)

    Returns:
        AIService instance
    """
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService(config)
    return _ai_service
