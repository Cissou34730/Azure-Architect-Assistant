"""
LlamaIndex Adapters for AIService

Provides LlamaIndex-compatible interfaces that delegate to the unified AIService.
This allows LlamaIndex code to continue working unchanged while using centralized
AI service configuration and monitoring.
"""

import asyncio
import logging
from typing import Any, List, Optional

from llama_index.core.base.llms.types import (
    CompletionResponse,
    CompletionResponseGen,
    ChatMessage as LlamaIndexChatMessage,
    ChatResponse,
    ChatResponseGen,
    MessageRole,
)
from llama_index.core.llms import CustomLLM
from llama_index.core.embeddings import BaseEmbedding

from ..ai_service import AIService
from ..interfaces import ChatMessage

logger = logging.getLogger(__name__)


class AIServiceLLM(CustomLLM):
    """
    LlamaIndex-compatible LLM that delegates to AIService.
    
    This adapter allows LlamaIndex to use the unified AIService while
    maintaining full compatibility with LlamaIndex's LLM interface.
    """
    
    ai_service: AIService
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_tokens: int = 1000
    
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(
        self,
        ai_service: AIService,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        **kwargs: Any
    ):
        """
        Initialize LlamaIndex adapter for AIService.
        
        Args:
            ai_service: The unified AIService instance
            model_name: Override model name (optional)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
        """
        super().__init__(
            ai_service=ai_service,
            model_name=model_name or "gpt-4o-mini",
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        logger.info(f"AIServiceLLM adapter initialized: model={self.model_name}")
    
    @property
    def metadata(self) -> dict:
        """LLM metadata."""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "is_chat_model": True,
        }
    
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """
        Synchronous completion call (required by LlamaIndex).
        
        Args:
            prompt: Text prompt for completion
            **kwargs: Additional parameters
            
        Returns:
            CompletionResponse with generated text
        """
        try:
            # Run async method in sync context
            response = asyncio.run(
                self.ai_service.complete(
                    prompt,
                    temperature=kwargs.get("temperature", self.temperature),
                    max_tokens=kwargs.get("max_tokens", self.max_tokens)
                )
            )
            return CompletionResponse(text=response)
        except RuntimeError:
            # Already in event loop, use run_until_complete
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(
                self.ai_service.complete(
                    prompt,
                    temperature=kwargs.get("temperature", self.temperature),
                    max_tokens=kwargs.get("max_tokens", self.max_tokens)
                )
            )
            return CompletionResponse(text=response)
    
    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        """Streaming not implemented for adapter."""
        raise NotImplementedError("Streaming not supported in adapter")
    
    def chat(self, messages: List[LlamaIndexChatMessage], **kwargs: Any) -> ChatResponse:
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
            ChatMessage(
                role=msg.role.value,
                content=msg.content or ""
            )
            for msg in messages
        ]
        
        try:
            # Run async method in sync context
            response = asyncio.run(
                self.ai_service.chat(
                    ai_messages,
                    temperature=kwargs.get("temperature", self.temperature),
                    max_tokens=kwargs.get("max_tokens", self.max_tokens)
                )
            )
            
            # Convert back to LlamaIndex format
            return ChatResponse(
                message=LlamaIndexChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=response.content
                ),
                raw=response.raw_response
            )
        except RuntimeError:
            # Already in event loop
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(
                self.ai_service.chat(
                    ai_messages,
                    temperature=kwargs.get("temperature", self.temperature),
                    max_tokens=kwargs.get("max_tokens", self.max_tokens)
                )
            )
            return ChatResponse(
                message=LlamaIndexChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=response.content
                ),
                raw=response.raw_response
            )
    
    def stream_chat(self, messages: List[LlamaIndexChatMessage], **kwargs: Any) -> ChatResponseGen:
        """Streaming not implemented for adapter."""
        raise NotImplementedError("Streaming not supported in adapter")


class AIServiceEmbedding(BaseEmbedding):
    """
    LlamaIndex-compatible embedding model that delegates to AIService.
    
    This adapter allows LlamaIndex to use the unified AIService for embeddings
    while maintaining full compatibility with LlamaIndex's embedding interface.
    """
    
    ai_service: AIService
    model_name: str = "text-embedding-3-small"
    
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(
        self,
        ai_service: AIService,
        model_name: Optional[str] = None,
        **kwargs: Any
    ):
        """
        Initialize LlamaIndex adapter for AIService embeddings.
        
        Args:
            ai_service: The unified AIService instance
            model_name: Override model name (optional)
        """
        super().__init__(
            ai_service=ai_service,
            model_name=model_name or "text-embedding-3-small",
            **kwargs
        )
        logger.info(f"AIServiceEmbedding adapter initialized: model={self.model_name}")
    
    @classmethod
    def class_name(cls) -> str:
        """Class name for serialization."""
        return "AIServiceEmbedding"
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """
        Get embedding for query text (required by LlamaIndex).
        
        Args:
            query: Query text to embed
            
        Returns:
            List of float values representing the embedding vector
        """
        try:
            # Run async method in sync context
            return asyncio.run(self.ai_service.embed_text(query))
        except RuntimeError:
            # Already in event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.ai_service.embed_text(query))
    
    def _get_text_embedding(self, text: str) -> List[float]:
        """
        Get embedding for document text (required by LlamaIndex).
        
        Args:
            text: Document text to embed
            
        Returns:
            List of float values representing the embedding vector
        """
        try:
            # Run async method in sync context
            return asyncio.run(self.ai_service.embed_text(text))
        except RuntimeError:
            # Already in event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.ai_service.embed_text(text))
    
    async def _aget_query_embedding(self, query: str) -> List[float]:
        """Async get query embedding."""
        return await self.ai_service.embed_text(query)
    
    async def _aget_text_embedding(self, text: str) -> List[float]:
        """Async get text embedding."""
        return await self.ai_service.embed_text(text)
    
    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts (batch).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            # Run async method in sync context
            return asyncio.run(self.ai_service.embed_batch(texts))
        except RuntimeError:
            # Already in event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.ai_service.embed_batch(texts))
