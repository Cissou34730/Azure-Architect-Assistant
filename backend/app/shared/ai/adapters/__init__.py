"""
LlamaIndex Adapters for AIService

These adapters allow LlamaIndex to use the unified AIService while
maintaining full compatibility with LlamaIndex's expected interfaces.
"""

from .llamaindex import AIServiceEmbedding, AIServiceLLM

__all__ = ["AIServiceEmbedding", "AIServiceLLM"]

