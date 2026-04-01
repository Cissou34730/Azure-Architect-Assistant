"""Tests for Azure OpenAI LLM & Embedding providers.

Mirrors the coverage of test_openai_llm_provider.py so that the Azure path has
parity with OpenAI.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from langchain_openai import AzureChatOpenAI

from app.services.ai.ai_service import AIService, AIServiceManager
from app.services.ai.config import AIConfig
from app.services.ai.interfaces import ChatMessage
from app.services.ai.providers.azure_openai_embedding import AzureOpenAIEmbeddingProvider
from app.services.ai.providers.azure_openai_llm import (
    AzureOpenAILLMProvider,
    _dedupe_deployments,
    _normalize_deployment_entry,
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _azure_config(**overrides) -> AIConfig:
    defaults = {
        "llm_provider": "azure",
        "embedding_provider": "azure",
        "azure_openai_endpoint": "https://aaaoi.openai.azure.com",
        "azure_openai_api_key": "test-azure-key",
        "azure_openai_api_version": "2024-02-15-preview",
        "azure_llm_deployment": "aaadp",
        "azure_llm_deployments": "",
        "azure_embedding_deployment": "text-embedding-3-small",
        "openai_embedding_model": "text-embedding-3-small",
    }
    defaults.update(overrides)
    return AIConfig(**defaults)


class _FakeAsyncChunkStream:
    def __init__(self, chunks: list[SimpleNamespace]) -> None:
        self._chunks = chunks

    def __aiter__(self):
        self._iterator = iter(self._chunks)
        return self

    async def __anext__(self):
        try:
            return next(self._iterator)
        except StopIteration as stop_iteration:
            raise StopAsyncIteration from stop_iteration


def _make_completion(
    content: str,
    model: str = "gpt-4o-mini",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
) -> SimpleNamespace:
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice], model=model, usage=usage)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def llm_provider(monkeypatch: pytest.MonkeyPatch) -> AzureOpenAILLMProvider:
    """Create Azure LLM provider with mocked AsyncAzureOpenAI client."""
    mock_completions = MagicMock()
    mock_chat = SimpleNamespace(completions=mock_completions)
    mock_client = SimpleNamespace(chat=mock_chat)

    monkeypatch.setattr(
        "app.services.ai.providers.azure_openai_client._azure_client",
        mock_client,
    )

    config = _azure_config()
    return AzureOpenAILLMProvider(config)


@pytest.fixture
def embedding_provider(monkeypatch: pytest.MonkeyPatch) -> AzureOpenAIEmbeddingProvider:
    """Create Azure Embedding provider with mocked AsyncAzureOpenAI client."""
    mock_embeddings = MagicMock()
    mock_client = SimpleNamespace(embeddings=mock_embeddings)

    monkeypatch.setattr(
        "app.services.ai.providers.azure_openai_client._azure_client",
        mock_client,
    )

    config = _azure_config()
    return AzureOpenAIEmbeddingProvider(config)


# ── LLM Provider Tests ──────────────────────────────────────────────────────

class TestAzureOpenAILLMProviderInit:
    def test_uses_deployment_name_as_model(self, llm_provider: AzureOpenAILLMProvider) -> None:
        assert llm_provider.model == "aaadp"

    def test_config_is_stored(self, llm_provider: AzureOpenAILLMProvider) -> None:
        assert llm_provider.config.azure_llm_deployment == "aaadp"


class TestAzureOpenAILLMChat:
    @pytest.mark.asyncio
    async def test_chat_returns_llm_response(
        self, llm_provider: AzureOpenAILLMProvider,
    ) -> None:
        fake_response = _make_completion("hello from azure")
        llm_provider.client.chat.completions.create = AsyncMock(return_value=fake_response)

        result = await llm_provider.chat(
            messages=[ChatMessage(role="user", content="hi")],
        )

        assert result.content == "hello from azure"
        assert result.model == "gpt-4o-mini"
        assert result.usage == {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        }

    @pytest.mark.asyncio
    async def test_chat_passes_deployment_as_model(
        self, llm_provider: AzureOpenAILLMProvider,
    ) -> None:
        fake_response = _make_completion("ok")
        llm_provider.client.chat.completions.create = AsyncMock(return_value=fake_response)

        await llm_provider.chat(
            messages=[ChatMessage(role="user", content="test")],
        )

        call_kwargs = llm_provider.client.chat.completions.create.await_args.kwargs
        assert call_kwargs["model"] == "aaadp"

    @pytest.mark.asyncio
    async def test_chat_supports_json_response_format(
        self, llm_provider: AzureOpenAILLMProvider,
    ) -> None:
        fake_response = _make_completion('{"status": "ok"}')
        llm_provider.client.chat.completions.create = AsyncMock(return_value=fake_response)

        result = await llm_provider.chat(
            messages=[ChatMessage(role="user", content="Return JSON")],
            response_format={"type": "json_object"},
        )

        assert result.content == '{"status": "ok"}'
        call_kwargs = llm_provider.client.chat.completions.create.await_args.kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_stream_yields_delta_chunks(
        self, llm_provider: AzureOpenAILLMProvider,
    ) -> None:
        def _make_chunk(delta_content: str | None) -> SimpleNamespace:
            delta = SimpleNamespace(content=delta_content)
            choice = SimpleNamespace(delta=delta)
            return SimpleNamespace(choices=[choice])

        fake_stream = _FakeAsyncChunkStream([
            _make_chunk("streamed "),
            _make_chunk("answer"),
            _make_chunk(None),
        ])
        llm_provider.client.chat.completions.create = AsyncMock(return_value=fake_stream)

        chunks: list[str] = []
        async for chunk in await llm_provider.chat(
            messages=[ChatMessage(role="user", content="stream this")],
            stream=True,
        ):
            chunks.append(chunk)

        assert chunks == ["streamed ", "answer"]


class TestAzureOpenAILLMModelListing:
    @pytest.mark.asyncio
    async def test_list_runtime_models_from_models_api(
        self, llm_provider: AzureOpenAILLMProvider, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """GET /openai/models returns available models, filtered to chat-capable."""
        fake_payload = {
            "data": [
                {"id": "gpt-4o-mini", "capabilities": {"chat_completion": True, "inference": True}},
                {"id": "gpt-4o", "capabilities": {"chat_completion": True, "inference": True}},
                {"id": "text-embedding-3-small", "capabilities": {"chat_completion": False, "inference": True}},
                {"id": "dall-e-3", "capabilities": {"chat_completion": False, "inference": True}},
                {"id": "o4-mini", "capabilities": {"chat_completion": True, "inference": True}},
            ],
        }
        fake_request = httpx.Request("GET", "https://aaaoi.openai.azure.com/openai/models")

        async def fake_get(self, url, *, params=None, headers=None):
            return httpx.Response(200, json=fake_payload, request=fake_request)

        monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

        result = await llm_provider.list_runtime_models()
        ids = [entry["id"] for entry in result]
        # Chat-capable models included
        assert "gpt-4o-mini" in ids
        assert "gpt-4o" in ids
        assert "o4-mini" in ids
        # Embedding and image models filtered out
        assert "text-embedding-3-small" not in ids
        assert "dall-e-3" not in ids

    @pytest.mark.asyncio
    async def test_list_runtime_models_includes_codex_models(
        self, llm_provider: AzureOpenAILLMProvider, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Codex models (inference-only, no chat_completion) must appear in the list."""
        fake_payload = {
            "data": [
                {"id": "gpt-4o-mini", "capabilities": {"chat_completion": True, "inference": True}},
                {"id": "gpt-5.3-codex-2026-02-20", "capabilities": {"chat_completion": False, "inference": True}},
                {"id": "gpt-5-codex-2025-09-15", "capabilities": {"chat_completion": False, "inference": True}},
                {"id": "codex-mini-2025-05-16", "capabilities": {"chat_completion": False, "inference": True}},
                {"id": "gpt-5.1-codex-max-2025-12-04", "capabilities": {"chat_completion": False, "inference": True}},
                {"id": "text-embedding-3-small", "capabilities": {"chat_completion": False, "inference": True}},
                {"id": "dall-e-3", "capabilities": {"chat_completion": False, "inference": True}},
                {"id": "whisper-001", "capabilities": {"chat_completion": False, "inference": True}},
                {"id": "sora-2025-05-02", "capabilities": {"chat_completion": False, "inference": True}},
            ],
        }
        fake_request = httpx.Request("GET", "https://aaaoi.openai.azure.com/openai/models")

        async def fake_get(self, url, *, params=None, headers=None):
            return httpx.Response(200, json=fake_payload, request=fake_request)

        monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

        result = await llm_provider.list_runtime_models()
        ids = [entry["id"] for entry in result]
        # Codex models MUST be included (inference-capable LLMs)
        assert "gpt-5.3-codex-2026-02-20" in ids
        assert "gpt-5-codex-2025-09-15" in ids
        assert "codex-mini-2025-05-16" in ids
        assert "gpt-5.1-codex-max-2025-12-04" in ids
        # Non-LLM models still excluded
        assert "text-embedding-3-small" not in ids
        assert "dall-e-3" not in ids
        assert "whisper-001" not in ids
        assert "sora-2025-05-02" not in ids

    @pytest.mark.asyncio
    async def test_list_runtime_models_includes_gpt5_models(
        self, llm_provider: AzureOpenAILLMProvider, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """GPT-5.3, GPT-5.4 and related models must be in the listing."""
        fake_payload = {
            "data": [
                {"id": "gpt-5.3-chat-2026-03-03", "capabilities": {"chat_completion": True, "inference": True}},
                {"id": "gpt-5.4-nano-2026-03-17", "capabilities": {"chat_completion": True, "inference": True}},
                {"id": "gpt-5.4-mini-2026-03-17", "capabilities": {"chat_completion": True, "inference": True}},
                {"id": "gpt-5.3-codex-2026-02-20", "capabilities": {"chat_completion": False, "inference": True}},
            ],
        }
        fake_request = httpx.Request("GET", "https://aaaoi.openai.azure.com/openai/models")

        async def fake_get(self, url, *, params=None, headers=None):
            return httpx.Response(200, json=fake_payload, request=fake_request)

        monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

        result = await llm_provider.list_runtime_models()
        ids = [entry["id"] for entry in result]
        assert "gpt-5.3-chat-2026-03-03" in ids
        assert "gpt-5.4-nano-2026-03-17" in ids
        assert "gpt-5.4-mini-2026-03-17" in ids
        assert "gpt-5.3-codex-2026-02-20" in ids

    @pytest.mark.asyncio
    async def test_list_runtime_models_merges_configured_deployments(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Configured deployments are always included alongside catalog models."""
        mock_client = SimpleNamespace(
            chat=SimpleNamespace(completions=MagicMock()),
        )
        monkeypatch.setattr(
            "app.services.ai.providers.azure_openai_client._azure_client",
            mock_client,
        )
        config = _azure_config(azure_llm_deployments="deploy-a,deploy-b")
        provider = AzureOpenAILLMProvider(config)

        fake_payload = {
            "data": [
                {"id": "gpt-4o-mini", "capabilities": {"chat_completion": True, "inference": True}},
                {"id": "gpt-4o", "capabilities": {"chat_completion": True, "inference": True}},
            ],
        }
        fake_request = httpx.Request("GET", "https://aaaoi.openai.azure.com/openai/models")

        async def fake_get(self, url, *, params=None, headers=None):
            return httpx.Response(200, json=fake_payload, request=fake_request)

        monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

        result = await provider.list_runtime_models()
        ids = [entry["id"] for entry in result]
        # Configured deployments present
        assert "aaadp" in ids
        assert "deploy-a" in ids
        assert "deploy-b" in ids
        # Catalog models also present
        assert "gpt-4o-mini" in ids
        assert "gpt-4o" in ids

    @pytest.mark.asyncio
    async def test_models_api_failure_falls_back_to_configured(
        self, llm_provider: AzureOpenAILLMProvider, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When /openai/models fails, fall back to configured deployments."""
        async def fake_get(self, url, *, params=None, headers=None):
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

        result = await llm_provider.list_runtime_models()
        assert result == [{"id": "aaadp", "model": "aaadp"}]

    @pytest.mark.asyncio
    async def test_models_api_returns_sorted_by_id(
        self, llm_provider: AzureOpenAILLMProvider, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Results are sorted alphabetically by model id."""
        fake_payload = {
            "data": [
                {"id": "gpt-4o-mini", "capabilities": {"chat_completion": True, "inference": True}},
                {"id": "gpt-4o", "capabilities": {"chat_completion": True, "inference": True}},
                {"id": "gpt-35-turbo", "capabilities": {"chat_completion": True, "inference": True}},
            ],
        }
        fake_request = httpx.Request("GET", "https://aaaoi.openai.azure.com/openai/models")

        async def fake_get(self, url, *, params=None, headers=None):
            return httpx.Response(200, json=fake_payload, request=fake_request)

        monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

        result = await llm_provider.list_runtime_models()
        ids = [entry["id"] for entry in result]
        assert ids == sorted(ids)

    @pytest.mark.asyncio
    async def test_no_credentials_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Missing endpoint/key skips API call and returns empty."""
        mock_client = SimpleNamespace(
            chat=SimpleNamespace(completions=MagicMock()),
        )
        monkeypatch.setattr(
            "app.services.ai.providers.azure_openai_client._azure_client",
            mock_client,
        )
        config = _azure_config(azure_openai_endpoint="", azure_openai_api_key="")
        provider = AzureOpenAILLMProvider(config)

        result = await provider._fetch_available_models()
        assert result == []

    @pytest.mark.asyncio
    async def test_models_api_uses_ga_api_version(
        self, llm_provider: AzureOpenAILLMProvider, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The models listing uses GA api-version 2024-10-21, not the configured preview."""
        captured_params: dict = {}
        fake_request = httpx.Request("GET", "https://aaaoi.openai.azure.com/openai/models")

        async def fake_get(self, url, *, params=None, headers=None):
            captured_params.update(params or {})
            return httpx.Response(200, json={"data": []}, request=fake_request)

        monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

        await llm_provider._fetch_available_models()
        assert captured_params.get("api-version") == "2024-10-21"


# ── Embedding Provider Tests ────────────────────────────────────────────────

class TestAzureOpenAIEmbeddingProviderInit:
    def test_uses_deployment_name_as_model(
        self, embedding_provider: AzureOpenAIEmbeddingProvider,
    ) -> None:
        assert embedding_provider.model == "text-embedding-3-small"

    def test_get_embedding_dimension_uses_openai_model_name(
        self, embedding_provider: AzureOpenAIEmbeddingProvider,
    ) -> None:
        """Dimension lookup uses the underlying OpenAI model name, not deployment name."""
        assert embedding_provider.get_embedding_dimension() == 1536

    def test_get_model_name_returns_deployment(
        self, embedding_provider: AzureOpenAIEmbeddingProvider,
    ) -> None:
        assert embedding_provider.get_model_name() == "text-embedding-3-small"


class TestAzureOpenAIEmbedding:
    @pytest.mark.asyncio
    async def test_embed_text_returns_vector(
        self, embedding_provider: AzureOpenAIEmbeddingProvider,
    ) -> None:
        fake_embedding = [0.1, 0.2, 0.3]
        fake_response = SimpleNamespace(
            data=[SimpleNamespace(embedding=fake_embedding)],
        )
        embedding_provider.client.embeddings.create = AsyncMock(return_value=fake_response)

        result = await embedding_provider.embed_text("hello")

        assert result == [0.1, 0.2, 0.3]
        embedding_provider.client.embeddings.create.assert_awaited_once_with(
            model="text-embedding-3-small",
            input="hello",
        )

    @pytest.mark.asyncio
    async def test_embed_batch_returns_vectors(
        self, embedding_provider: AzureOpenAIEmbeddingProvider,
    ) -> None:
        fake_response = SimpleNamespace(
            data=[
                SimpleNamespace(embedding=[0.1, 0.2]),
                SimpleNamespace(embedding=[0.3, 0.4]),
            ],
        )
        embedding_provider.client.embeddings.create = AsyncMock(return_value=fake_response)

        result = await embedding_provider.embed_batch(["hello", "world"])

        assert result == [[0.1, 0.2], [0.3, 0.4]]

    @pytest.mark.asyncio
    async def test_embed_batch_rejects_zero_batch_size(
        self, embedding_provider: AzureOpenAIEmbeddingProvider,
    ) -> None:
        with pytest.raises(ValueError, match="batch_size must be positive"):
            await embedding_provider.embed_batch(["hello"], batch_size=0)


# ── Unit tests for helper functions ──────────────────────────────────────────

class TestNormalizeDeploymentEntry:
    def test_valid_llm_entry(self) -> None:
        result = _normalize_deployment_entry({"id": "my-deploy", "model": "gpt-4o-mini"})
        assert result == {"id": "my-deploy", "model": "gpt-4o-mini"}

    def test_filters_embedding_model(self) -> None:
        result = _normalize_deployment_entry({"id": "embed", "model": "text-embedding-3-small"})
        assert result is None

    def test_missing_id(self) -> None:
        result = _normalize_deployment_entry({"model": "gpt-4"})
        assert result is None

    def test_blank_id(self) -> None:
        result = _normalize_deployment_entry({"id": "", "model": "gpt-4"})
        assert result is None

    def test_non_dict_input(self) -> None:
        result = _normalize_deployment_entry("not-a-dict")
        assert result is None

    def test_missing_model_uses_deployment_id(self) -> None:
        result = _normalize_deployment_entry({"id": "my-deploy"})
        assert result == {"id": "my-deploy", "model": "my-deploy"}


class TestDedupeDeployments:
    def test_removes_duplicates(self) -> None:
        result = _dedupe_deployments(["a", "b", "a", "c"])
        assert [r["id"] for r in result] == ["a", "b", "c"]

    def test_empty_list(self) -> None:
        result = _dedupe_deployments([])
        assert result == []


# ── AIService integration: Azure LangChain adapter ──────────────────────────

class TestAzureChatLLMCreation:
    def test_create_chat_llm_returns_azure_chat_openai(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "app.services.ai.providers.azure_openai_client._azure_client",
            MagicMock(),
        )

        config = _azure_config()
        service = AIService(config)

        chat_llm = service.create_chat_llm()

        assert isinstance(chat_llm, AzureChatOpenAI)

    def test_create_chat_llm_passes_deployment(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "app.services.ai.providers.azure_openai_client._azure_client",
            MagicMock(),
        )

        config = _azure_config()
        service = AIService(config)

        chat_llm = service.create_chat_llm(temperature=0.5)

        assert chat_llm.deployment_name == "aaadp"


# ── AIConfig: Azure validation ──────────────────────────────────────────────

class TestAzureConfigValidation:
    def test_validate_passes_with_all_fields(self) -> None:
        config = _azure_config()
        config.validate_provider_config()  # should not raise

    def test_validate_fails_without_endpoint(self) -> None:
        config = _azure_config(azure_openai_endpoint="")
        with pytest.raises(ValueError, match="Azure endpoint"):
            config.validate_provider_config()

    def test_validate_fails_without_api_key(self) -> None:
        config = _azure_config(azure_openai_api_key="")
        with pytest.raises(ValueError, match="Azure endpoint"):
            config.validate_provider_config()

    def test_validate_fails_without_deployment(self) -> None:
        config = _azure_config(azure_llm_deployment="")
        with pytest.raises(ValueError, match="Azure endpoint"):
            config.validate_provider_config()

    def test_validate_fails_without_embedding_deployment_when_azure_embedding(self) -> None:
        config = _azure_config(azure_embedding_deployment="")
        with pytest.raises(ValueError, match=r"Azure.*embedding"):
            config.validate_provider_config()


# ── Build-config-for-selection: Azure path ──────────────────────────────────

class TestBuildConfigForSelectionAzure:
    def test_updates_azure_llm_deployment(self) -> None:
        base = _azure_config()
        new_config = AIServiceManager._build_config_for_selection(
            "azure", "new-deployment", base_config=base,
        )

        assert new_config.azure_llm_deployment == "new-deployment"
        assert new_config.llm_provider == "azure"

    def test_preserves_other_fields(self) -> None:
        base = _azure_config()
        new_config = AIServiceManager._build_config_for_selection(
            "azure", "new-deployment", base_config=base,
        )

        assert new_config.azure_openai_endpoint == "https://aaaoi.openai.azure.com"
        assert new_config.azure_openai_api_key == "test-azure-key"
        assert new_config.azure_embedding_deployment == "text-embedding-3-small"
