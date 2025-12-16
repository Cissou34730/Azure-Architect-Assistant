"""Operations package for MCP service."""

from .learn_operations import (
    fetch_documentation,
    get_azure_guidance,
    search_code_samples,
    search_microsoft_docs,
)

__all__ = [
    "search_microsoft_docs",
    "fetch_documentation",
    "search_code_samples",
    "get_azure_guidance",
]
