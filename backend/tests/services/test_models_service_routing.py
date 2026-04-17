from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.shared.ai.config import AIConfig
from app.shared.ai.models_service import ModelsService


@pytest.mark.asyncio
async def test_models_service_uses_runtime_listing_for_foundry_provider(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = AIConfig(
        llm_provider="foundry",
        embedding_provider="foundry",
        foundry_endpoint="https://example.services.ai.azure.com",
        foundry_api_key="test-foundry-key",
        foundry_resource_id="/subscriptions/test/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/foundry",
        foundry_model="gpt-5.3-chat",
        foundry_embedding_model="text-embedding-3-small",
    )
    service = ModelsService(cache_path=tmp_path / "models_cache.json", config=config)
    runtime_service = SimpleNamespace(
        list_llm_runtime_models=AsyncMock(
            return_value=[
                {"id": "gpt-5.3-chat", "model": "gpt-5.3-chat"},
                {"id": "Phi-4", "model": "Phi-4"},
            ]
        )
    )

    monkeypatch.setattr(
        "app.shared.ai.models_service.AIServiceManager.create_probe",
        lambda _config: runtime_service,
    )

    models, _ = await service.get_available_models(force_refresh=True)

    model_ids = [model.id for model in models]
    assert model_ids == ["gpt-5.3-chat", "Phi-4"]


@pytest.mark.asyncio
async def test_models_service_reuses_cached_models_for_foundry_provider(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = AIConfig(
        llm_provider="foundry",
        embedding_provider="foundry",
        foundry_endpoint="https://example.services.ai.azure.com",
        foundry_api_key="test-foundry-key",
        foundry_resource_id="/subscriptions/test/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/foundry",
        foundry_model="gpt-5.3-chat",
        foundry_embedding_model="text-embedding-3-small",
    )
    service = ModelsService(cache_path=tmp_path / "models_cache.json", config=config)
    runtime_service = SimpleNamespace(
        list_llm_runtime_models=AsyncMock(
            side_effect=[
                [{"id": "gpt-5.3-chat", "model": "gpt-5.3-chat"}],
                RuntimeError("foundry unavailable"),
            ]
        )
    )
    monkeypatch.setattr(
        "app.shared.ai.models_service.AIServiceManager.create_probe",
        lambda _config: runtime_service,
    )

    first_models, _ = await service.get_available_models(force_refresh=True)
    assert [model.id for model in first_models] == ["gpt-5.3-chat"]

    cached_models, _ = await service.get_available_models(force_refresh=False)
    assert [model.id for model in cached_models] == ["gpt-5.3-chat"]
    assert runtime_service.list_llm_runtime_models.await_count == 1


@pytest.mark.asyncio
async def test_models_service_cache_only_returns_copilot_fallback_models(
    tmp_path,
) -> None:
    config = AIConfig(
        llm_provider="copilot",
        embedding_provider="openai",
        openai_api_key="test-openai-key",
        copilot_default_model="gpt-5.2",
        copilot_allowed_models="gpt-5.2,gpt-5-mini",
    )
    service = ModelsService(cache_path=tmp_path / "models_cache.json", config=config)

    models, _ = await service.get_available_models(cache_only=True)

    assert [model.id for model in models] == ["gpt-5.2", "gpt-5-mini"]

