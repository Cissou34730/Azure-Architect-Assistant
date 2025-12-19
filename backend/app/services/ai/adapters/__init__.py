"""
LlamaIndex Adapters for AIService

These adapters allow LlamaIndex to use the unified AIService while
maintaining full compatibility with LlamaIndex's expected interfaces.
"""

from .llamaindex import AIServiceLLM, AIServiceEmbedding

__all__ = ["AIServiceLLM", "AIServiceEmbedding"]
