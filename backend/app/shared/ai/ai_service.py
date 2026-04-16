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
    CopilotLLMProvider,
    FoundryEmbeddingProvider,
    FoundryLLMProvider,
    OpenAIEmbeddingProvider,
    OpenAILLMProvider,
    reset_copilot_runtime,
    reset_foundry_client,
    reset_github_models_client,
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
        self._router = AIRouter(
            primary_llm=self._llm_provider,
            primary_embedding=self._embedding_provider,
        )

        logger.info(
            "AIService initialized - LLM: %s, Embedding: %s",
            self.config.llm_provider,
            self.config.embedding_provider,
        )

    def create_chat_llm(self, *, temperature: float | None = None, **kwargs: Any) -> Any:
        """Create a provider-selected LangChain chat model for native agent runtimes."""
        effective_temperature = (
            temperature if temperature is not None else self.config.default_temperature
        )

        if self.config.llm_provider == "foundry":
            from langchain_openai import AzureChatOpenAI  # noqa: PLC0415

            return AzureChatOpenAI(
                azure_deployment=self.config.foundry_model,
                api_version=self.config.foundry_api_version,
                azure_endpoint=self.config.foundry_endpoint,
                api_key=self.config.foundry_api_key,
                temperature=effective_temperature,
                **kwargs,
            )

        if self.config.llm_provider == "openai":
            from langchain_openai import ChatOpenAI  # noqa: PLC0415

            return ChatOpenAI(
                model=self.config.openai_llm_model,
                temperature=effective_temperature,
                openai_api_key=self.config.openai_api_key,
                **kwargs,
            )

        if self.config.llm_provider == "copilot":
            from .providers.copilot_chat_model import CopilotChatModel  # noqa: PLC0415

            model = CopilotChatModel(
                model_name=self.config.copilot_default_model,
                timeout=self.config.copilot_request_timeout,
            )
            model._config = self.config
            return model

        raise NotImplementedError(
            f"Native LangChain adapter not implemented for provider: {self.config.llm_provider}"
        )

    def _create_llm_provider(self, provider_name: str) -> LLMProvider:
        """Factory method to create LLM provider based on config."""
        if provider_name == "openai":
            return OpenAILLMProvider(self.config)
        elif provider_name == "foundry":
            return FoundryLLMProvider(self.config)
        elif provider_name == "copilot":
            return CopilotLLMProvider(self.config)
        elif provider_name == "anthropic":
            # TODO: Implement AnthropicLLMProvider
            raise NotImplementedError("Anthropic LLM provider not yet implemented")
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")

    def _create_embedding_provider(self, provider_name: str) -> EmbeddingProvider:
        """Factory method to create embedding provider based on config."""
        if provider_name == "openai":
            return OpenAIEmbeddingProvider(self.config)
        elif provider_name == "foundry":
            return FoundryEmbeddingProvider(self.config)
        else:
            raise ValueError(f"Unknown embedding provider: {provider_name}")

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

        use_model_default_temperature = bool(kwargs.pop("use_model_default_temperature", False))
        temp = None if use_model_default_temperature else (
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
        use_model_default_temperature = bool(kwargs.pop("use_model_default_temperature", False))
        temp = None if use_model_default_temperature else (
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

    def get_llm_provider_name(self) -> str:
        """Get current LLM provider name."""
        return self.config.llm_provider

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

    async def list_llm_runtime_models(self) -> list[dict[str, Any]]:
        """List runtime-selectable model identities for the active LLM provider."""
        return await self._llm_provider.list_runtime_models()


class AIServiceManager:
    """
    Manages the AIService singleton instance.

    SINGLETON RATIONALE:
    - Provider abstraction: Manages OpenAI, AI Foundry, Anthropic clients
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
            from app.shared.config.app_settings import get_app_settings  # noqa: PLC0415
            await asyncio.sleep(get_app_settings().ai_reinit_grace_sleep)

            try:
                # Build new config via immutable model_copy (AIConfig is a frozen BaseModel)
                base_config = AIConfig.default()
                await cls._reinitialize(
                    cls._build_config_for_selection(
                        base_config.llm_provider,
                        new_model,
                        base_config=base_config,
                    )
                )

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
    async def reinitialize_with_selection(cls, provider_name: str, model_id: str) -> None:
        async with cls._lock:
            base_config = AIConfig.default()
            new_config = cls._build_config_for_selection(
                provider_name,
                model_id,
                base_config=base_config,
            )
            await cls._reinitialize(new_config)

    @classmethod
    async def _reinitialize(cls, new_config: AIConfig) -> None:
        new_config.validate_provider_config()
        reset_openai_client()
        reset_foundry_client()
        reset_github_models_client()
        await reset_copilot_runtime()
        cls._instance = AIService(new_config)
        cls._notify_dependents()

    @staticmethod
    def _build_config_for_selection(
        provider_name: str,
        model_id: str,
        *,
        base_config: AIConfig,
    ) -> AIConfig:
        if provider_name == "azure":
            raise ValueError("Provider 'azure' is no longer supported. Use 'foundry'.")
        if provider_name not in {"openai", "foundry", "copilot"}:
            raise ValueError(f"Unknown runtime AI provider: {provider_name}")

        updates: dict[str, str] = {"llm_provider": provider_name}
        if provider_name == "foundry":
            updates["foundry_model"] = model_id
        elif provider_name == "copilot":
            updates["copilot_default_model"] = model_id
        else:
            updates["openai_llm_model"] = model_id
        return base_config.model_copy(update=updates)

    @classmethod
    def _notify_dependents(cls) -> None:
        """Clear downstream singleton caches that hold a reference to AIService."""
        try:
            from app.shared.ai.llm_service import LLMServiceSingleton  # noqa: PLC0415
            LLMServiceSingleton.set_instance(None)
            logger.debug("Cleared LLMService singleton instance")
        except ImportError:
            logger.debug("LLMServiceSingleton not available; skipping dependent cache clear")


def get_ai_service(config: AIConfig | None = None) -> AIService:
    """
    Get or create AIService singleton.

    Args:
        config: Optional configuration (only used on first call)

    Returns:
        AIService instance
    """
    return AIServiceManager.get_instance(config)

