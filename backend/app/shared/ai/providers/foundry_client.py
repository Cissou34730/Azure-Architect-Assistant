"""Shared AsyncAzureOpenAI client for AI Foundry-backed inference."""

from __future__ import annotations

import logging

from openai import AsyncAzureOpenAI

from ..config import AIConfig

logger = logging.getLogger(__name__)

_foundry_client: AsyncAzureOpenAI | None = None


def get_foundry_client(config: AIConfig) -> AsyncAzureOpenAI:
    """Return the process-wide shared AI Foundry client."""
    global _foundry_client  # noqa: PLW0603
    if _foundry_client is None:
        _foundry_client = AsyncAzureOpenAI(
            api_key=config.foundry_api_key,
            api_version=config.foundry_api_version,
            azure_endpoint=config.foundry_endpoint,
            timeout=config.openai_timeout,
            max_retries=config.openai_max_retries,
        )
        logger.info(
            "Shared AI Foundry client created (endpoint=%s, api_version=%s, timeout=%.1fs, max_retries=%d)",
            config.foundry_endpoint,
            config.foundry_api_version,
            config.openai_timeout,
            config.openai_max_retries,
        )
    return _foundry_client


def reset_foundry_client() -> None:
    """Reset the shared AI Foundry client singleton."""
    global _foundry_client  # noqa: PLW0603
    _foundry_client = None
