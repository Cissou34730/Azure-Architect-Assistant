import pytest

from app.services.ai.config import AIConfig
from app.services.models_service import ModelsService


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

    models, _ = await service._get_azure_models()

    model_ids = [model.id for model in models]
    assert model_ids == [
        "primary-deployment",
        "secondary-deployment",
        "tertiary-deployment",
    ]
