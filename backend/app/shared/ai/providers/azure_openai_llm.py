"""
Azure OpenAI LLM Provider Implementation.
"""

import logging
from typing import Any

import httpx

from ..config import AIConfig
from .azure_openai_client import get_azure_openai_client
from .openai_llm import OpenAILLMProvider

logger = logging.getLogger(__name__)

# The /openai/models endpoint requires a GA api-version.
_MODELS_API_VERSION = "2024-10-21"


# Model families that are NOT LLMs and should be excluded from the model selector.
_EXCLUDED_MODEL_PREFIXES = (
    "text-embedding",
    "dall-e",
    "whisper",
    "sora",
    "aoai-sora",
    "gpt-4o-realtime",
    "gpt-4o-mini-realtime",
    "gpt-realtime",
    "gpt-4o-transcribe",
    "gpt-4o-mini-transcribe",
    "gpt-4o-mini-tts",
    "gpt-audio",
    "computer-use",
    "model-router",
)


def _is_excluded_model(model_id: str) -> bool:
    """Return True for models that should not appear in the LLM selector."""
    lower = model_id.lower()
    return any(lower.startswith(prefix) for prefix in _EXCLUDED_MODEL_PREFIXES)


def _normalize_deployment_entry(item: object) -> dict[str, str] | None:
    if not isinstance(item, dict):
        return None

    deployment = item.get("id")
    if not isinstance(deployment, str) or not deployment.strip():
        return None

    model_name = item.get("model")
    normalized_model = model_name.strip() if isinstance(model_name, str) else ""
    if normalized_model.lower().startswith("text-embedding"):
        return None

    deployment_id = deployment.strip()
    return {
        "id": deployment_id,
        "model": normalized_model or deployment_id,
    }


def _dedupe_deployments(deployments: list[str]) -> list[dict[str, str]]:
    unique_deployments: list[str] = []
    seen: set[str] = set()
    for deployment in deployments:
        if deployment in seen:
            continue
        seen.add(deployment)
        unique_deployments.append(deployment)
    return [{"id": deployment, "model": deployment} for deployment in unique_deployments]


class AzureOpenAILLMProvider(OpenAILLMProvider):
    """Azure OpenAI implementation of LLM provider."""

    def __init__(self, config: AIConfig):
        self.config = config
        self.client = get_azure_openai_client(config)
        self.model = config.azure_llm_deployment
        logger.info("Azure OpenAI LLM Provider initialized with deployment: %s", self.model)

    async def _fetch_available_models(self) -> list[dict[str, str]]:
        """Fetch all chat-capable models from the Azure OpenAI /openai/models endpoint.

        Uses the GA ``2024-10-21`` api-version regardless of the configured
        preview version.  Filters for models whose ``capabilities`` include
        both ``chat_completion`` and ``inference``.
        """
        endpoint = (self.config.azure_openai_endpoint or "").rstrip("/")
        api_key = self.config.azure_openai_api_key
        if not (endpoint and api_key):
            return []

        url = f"{endpoint}/openai/models"
        headers: dict[str, str] = {"api-key": api_key}
        params: dict[str, str] = {"api-version": _MODELS_API_VERSION}
        timeout = min(10.0, float(self.config.openai_timeout))

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
        except Exception as exc:
            logger.warning("Azure /openai/models fetch failed: %s", exc)
            return []

        models: list[dict[str, Any]] = resp.json().get("data", [])
        llm_models: list[dict[str, str]] = []
        for model in models:
            caps = model.get("capabilities") or {}
            if not caps.get("inference"):
                continue
            model_id = model.get("id", "")
            if not model_id or _is_excluded_model(model_id):
                continue
            llm_models.append({"id": model_id, "model": model_id})

        llm_models.sort(key=lambda m: m["id"])
        return llm_models

    async def _fetch_deployments(self) -> list[dict[str, str]]:
        """Fetch actual deployed inference endpoints from the Azure data-plane deployments API.

        Calls ``GET {endpoint}/openai/deployments?api-version=...`` and returns
        only succeeded LLM deployments as ``[{"id": deployment_name, "model": base_model_id}]``.
        Returns an empty list when credentials are absent or the request fails.
        """
        endpoint = (self.config.azure_openai_endpoint or "").rstrip("/")
        api_key = self.config.azure_openai_api_key
        if not (endpoint and api_key):
            return []

        url = f"{endpoint}/openai/deployments"
        headers: dict[str, str] = {"api-key": api_key}
        params: dict[str, str] = {"api-version": _MODELS_API_VERSION}
        # Short timeout: this is a non-blocking discovery call; we fall back
        # to configured deployments if the endpoint is slow or unreachable.
        timeout = min(5.0, float(self.config.openai_timeout))

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
        except Exception as exc:
            logger.warning("Azure /openai/deployments fetch failed: %s", exc)
            return []

        raw: list[Any] = resp.json().get("data", [])
        deployments: list[dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            if item.get("status") != "succeeded":
                continue
            deployment_id = (item.get("id") or "").strip()
            if not deployment_id:
                continue
            base_model = (item.get("model") or "").strip() or deployment_id
            if _is_excluded_model(base_model):
                continue
            deployments.append({"id": deployment_id, "model": base_model})

        return deployments

    def _configured_deployments(self) -> list[dict[str, str]]:
        deployments: list[str] = []
        if self.config.azure_llm_deployment:
            deployments.append(self.config.azure_llm_deployment)
        if self.config.azure_llm_deployments:
            deployments.extend(
                [item.strip() for item in self.config.azure_llm_deployments.split(",") if item.strip()]
            )
        return _dedupe_deployments(deployments)

    async def list_runtime_models(self) -> list[dict[str, str]]:
        """List runtime-selectable Azure deployment identities.

        Queries the Azure data-plane ``/openai/deployments`` endpoint to
        discover all successfully-deployed LLM inference endpoints.  Falls back
        to deployment IDs configured via env vars when the API is unreachable
        or returns no LLM deployments.
        """
        deployments = await self._fetch_deployments()

        if deployments:
            return deployments

        # Fall back to configured deployment IDs (env vars)
        configured = self._configured_deployments()
        if not configured:
            logger.warning(
                "Azure runtime model selection requires configured deployment ids; "
                "set AI_AZURE_LLM_DEPLOYMENT and optionally AI_AZURE_LLM_DEPLOYMENTS."
            )
        return configured
