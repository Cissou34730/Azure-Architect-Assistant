"""
Unified AI Service Layer
Provides centralized access to LLM and Embedding providers with pluggable backends.
"""

from .ai_service import AIService, get_ai_service
from .config import AIConfig
from .interfaces import ChatMessage, EmbeddingProvider, LLMProvider, LLMResponse

__all__ = [
    "AIConfig",
    "AIService",
    "ChatMessage",
    "EmbeddingProvider",
    "LLMProvider",
    "LLMResponse",
    "get_ai_service",
]

