import pytest

from app.shared.ai.config import AIConfig
from app.shared.ai.models_service import ModelsService


@pytest.mark.asyncio
async def test_models_service_uses_azure_deployments_for_azure_provider(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = AIConfig(
        llm_provider="azure",
        embedding_provider="azure",
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_api_key="test-azure-key",
        azure_llm_deployment="primary-deployment",
        azure_llm_deployments="secondary-deployment, tertiary-deployment",
        azure_embedding_deployment="embedding-deployment",
    )
    service = ModelsService(cache_path=tmp_path / "models_cache.json", config=config)
    async def _no_live_deployments() -> list[dict[str, str]]:
        return []

    monkeypatch.setattr(service, "_fetch_azure_deployments_data_plane", _no_live_deployments)

    models = await service._fetch_azure_models()

    model_ids = [model.id for model in models]
    assert model_ids == [
        "primary-deployment",
        "secondary-deployment",
        "tertiary-deployment",
    ]


@pytest.mark.asyncio
async def test_models_service_reuses_cached_models_for_azure_provider(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = AIConfig(
        llm_provider="azure",
        embedding_provider="openai",
        openai_api_key="test-openai-key",
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_api_key="test-azure-key",
        azure_llm_deployment="primary-deployment",
    )
    service = ModelsService(cache_path=tmp_path / "models_cache.json", config=config)

    async def _live_models() -> list[dict[str, str]]:
        return [{"id": "primary-deployment", "model": "gpt-4o"}]

    monkeypatch.setattr(service, "_fetch_azure_deployments_data_plane", _live_models)

    first_models, _ = await service.get_available_models(force_refresh=True)
    assert [model.id for model in first_models] == ["primary-deployment"]

    async def _boom() -> list[dict[str, str]]:
        raise RuntimeError("azure unavailable")

    monkeypatch.setattr(service, "_fetch_azure_deployments_data_plane", _boom)

    cached_models, _ = await service.get_available_models(force_refresh=False)
    assert [model.id for model in cached_models] == ["primary-deployment"]


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

