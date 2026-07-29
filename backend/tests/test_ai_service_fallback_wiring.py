"""Tests for AIService fallback factory construction."""

from __future__ import annotations

import pytest

from app.shared.ai.ai_service import AIService
from app.shared.ai.config import AIConfig


def _config(**overrides) -> AIConfig:
    base = {
        "llm_provider": "openai",
        "embedding_provider": "openai",
        "openai_api_key": "sk-test",
    }
    base.update(overrides)
    return AIConfig(**base)


def test_no_fallbacks_by_default() -> None:
    service = AIService(_config())
    assert service._router._fallback_llm_factories == {}


def test_fallback_built_when_configured_and_credentialed() -> None:
    service = AIService(
        _config(
            llm_fallback_providers="foundry",
            foundry_endpoint="https://example.openai.azure.com",
            foundry_api_key="foundry-key",
        )
    )
    assert list(service._router._fallback_llm_factories.keys()) == ["foundry"]


def test_fallback_skipped_when_credentials_missing() -> None:
    service = AIService(_config(llm_fallback_providers="foundry"))
    assert service._router._fallback_llm_factories == {}


def test_primary_provider_excluded_from_fallbacks() -> None:
    service = AIService(
        _config(
            llm_fallback_providers="openai,foundry",
            foundry_endpoint="https://example.openai.azure.com",
            foundry_api_key="foundry-key",
        )
    )
    assert list(service._router._fallback_llm_factories.keys()) == ["foundry"]


def test_unknown_fallback_provider_raises_on_invocation() -> None:
    service = AIService(_config(llm_fallback_providers="anthropic"))
    # anthropic has no credential check -> skipped as unconfigured
    assert service._router._fallback_llm_factories == {}
