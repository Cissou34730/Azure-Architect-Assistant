"""Shared AsyncOpenAI client for the GitHub Models API."""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from ..config import AIConfig

logger = logging.getLogger(__name__)

_github_models_client: AsyncOpenAI | None = None


def get_github_models_client(config: AIConfig) -> AsyncOpenAI:
    """Return the process-wide shared client for GitHub Models API calls."""
    global _github_models_client  # noqa: PLW0603
    if _github_models_client is None:
        _github_models_client = AsyncOpenAI(
            api_key=config.copilot_token,
            base_url="https://models.github.ai/inference",
            timeout=config.copilot_request_timeout,
            max_retries=0,
        )
        logger.info(
            "Shared GitHub Models client created (timeout=%.1fs)",
            config.copilot_request_timeout,
        )
    return _github_models_client


def reset_github_models_client() -> None:
    """Reset the shared GitHub Models client singleton."""
    global _github_models_client  # noqa: PLW0603
    _github_models_client = None
