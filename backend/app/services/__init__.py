"""
Services Package
Business logic and orchestration layer.

NOTE: Singleton pattern used intentionally for in-memory index caching.
"""

from .llm_service import LLMService, get_llm_service

__all__ = [
    "LLMService",
    "get_llm_service",
]
