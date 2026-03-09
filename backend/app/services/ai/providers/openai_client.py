"""
Shared AsyncOpenAI client singleton.

All code that needs to reach the OpenAI REST API (LLM, embeddings, model listing)
must obtain the client through ``get_openai_client``.  This guarantees:
- A single ``AsyncOpenAI`` instance per process (connection pool reuse).
- Consistent timeout / retry configuration sourced from ``AIConfig``.
- ``max_retries=0`` so SDK-level silent retries never mask timeout errors;
  callers are responsible for their own explicit retry strategy.
"""

import logging

from openai import AsyncOpenAI

from ..config import AIConfig

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def get_openai_client(config: AIConfig) -> AsyncOpenAI:
    """Return the process-wide shared ``AsyncOpenAI`` client.

    The client is created on first call and reused on subsequent calls.
    Configuration (API key, timeout) is read from *config* on first call only.
    """
    global _client  # noqa: PLW0603
    if _client is None:
        _client = AsyncOpenAI(
            api_key=config.openai_api_key,
            project=(config.openai_project or None),
            organization=(config.openai_organization or None),
            timeout=config.openai_timeout,
            max_retries=config.openai_max_retries,
        )
        logger.info(
            "Shared AsyncOpenAI client created (project=%s, org=%s, timeout=%.1fs, max_retries=%d)",
            (config.openai_project or "<default>"),
            (config.openai_organization or "<default>"),
            config.openai_timeout,
            config.openai_max_retries,
        )
    return _client


def reset_openai_client() -> None:
    """Reset the shared client singleton so the next call recreates it.

    Call this whenever connection parameters (API key, timeout) change -
    for example after a model-switching reinitialisation.
    """
    global _client  # noqa: PLW0603
    _client = None
