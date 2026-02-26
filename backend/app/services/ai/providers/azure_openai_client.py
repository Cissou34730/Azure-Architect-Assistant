"""
Shared AsyncAzureOpenAI client singleton.

All Azure OpenAI traffic should use this client to reuse HTTP connections and
apply consistent timeout/retry configuration.
"""

import logging

from openai import AsyncAzureOpenAI

from ..config import AIConfig

logger = logging.getLogger(__name__)

_azure_client: AsyncAzureOpenAI | None = None


def get_azure_openai_client(config: AIConfig) -> AsyncAzureOpenAI:
    """Return process-wide shared AsyncAzureOpenAI client."""
    global _azure_client
    if _azure_client is None:
        _azure_client = AsyncAzureOpenAI(
            api_key=config.azure_openai_api_key,
            api_version=config.azure_openai_api_version,
            azure_endpoint=config.azure_openai_endpoint,
            timeout=config.openai_timeout,
            max_retries=config.openai_max_retries,
        )
        logger.info(
            "Shared AsyncAzureOpenAI client created (endpoint=%s, api_version=%s, timeout=%.1fs, max_retries=%d)",
            config.azure_openai_endpoint,
            config.azure_openai_api_version,
            config.openai_timeout,
            config.openai_max_retries,
        )
    return _azure_client
