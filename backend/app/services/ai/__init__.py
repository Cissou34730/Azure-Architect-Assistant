"""
Unified AI Service Layer
Provides centralized access to LLM and Embedding providers with pluggable backends.
"""

from .interfaces import LLMProvider, EmbeddingProvider
from .ai_service import AIService, get_ai_service
from .config import AIConfig

__all__ = [
    'LLMProvider',
    'EmbeddingProvider',
    'AIService',
    'AIConfig',
    'get_ai_service',
]
