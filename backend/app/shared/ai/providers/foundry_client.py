"""Shared OpenAI v1 client for AI Foundry-backed inference."""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from ..config import AIConfig

logger = logging.getLogger(__name__)

_foundry_client: AsyncOpenAI | None = None


def build_foundry_v1_base_url(endpoint: str) -> str:
    """Return the Microsoft Foundry/OpenAI v1 base URL for an account endpoint."""
    normalized = endpoint.strip().rstrip("/")
    if not normalized:
        return ""
    if normalized.endswith("/openai/v1"):
        return f"{normalized}/"
    if normalized.endswith("/openai"):
        return f"{normalized}/v1/"
    return f"{normalized}/openai/v1/"


def get_foundry_client(config: AIConfig) -> AsyncOpenAI:
    """Return the process-wide shared AI Foundry client."""
    global _foundry_client  # noqa: PLW0603
    if _foundry_client is None:
        base_url = build_foundry_v1_base_url(config.foundry_endpoint)
        _foundry_client = AsyncOpenAI(
            api_key=config.foundry_api_key,
            base_url=base_url,
            timeout=config.openai_timeout,
            max_retries=config.openai_max_retries,
        )
        logger.info(
            "Shared AI Foundry v1 client created (base_url=%s, timeout=%.1fs, max_retries=%d)",
            base_url,
            config.openai_timeout,
            config.openai_max_retries,
        )
    return _foundry_client


def reset_foundry_client() -> None:
    """Reset the shared AI Foundry client singleton."""
    global _foundry_client  # noqa: PLW0603
    _foundry_client = None
