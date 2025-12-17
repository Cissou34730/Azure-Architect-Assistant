"""
AI Provider Interfaces
Abstract base classes for LLM and Embedding providers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator, Optional
from dataclasses import dataclass


@dataclass
class ChatMessage:
    """Standardized chat message format."""
    role: str  # 'system', 'user', 'assistant'
    content: str


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None  # {'prompt_tokens', 'completion_tokens', 'total_tokens'}
    finish_reason: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse | AsyncIterator[str]:
        """
        Generate chat completion.
        
        Args:
            messages: List of chat messages
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Provider-specific parameters
            
        Returns:
            LLMResponse for non-streaming, AsyncIterator[str] for streaming
        """
        pass
    
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Simple text completion.
        
        Args:
            prompt: Text prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters
            
        Returns:
            Generated text
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the current model name."""
        pass


@dataclass
class EmbeddingResponse:
    """Standardized embedding response."""
    embeddings: List[List[float]]
    model: str
    usage: Optional[Dict[str, int]] = None  # {'prompt_tokens', 'total_tokens'}


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
        """
        pass
    
    @abstractmethod
    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with batching.
        
        Args:
            texts: List of input texts
            batch_size: Number of texts to process per batch
            
        Returns:
            List of embedding vectors
        """
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this provider."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the current embedding model name."""
        pass
