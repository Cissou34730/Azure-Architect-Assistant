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

    async def _fetch_remote_deployments(self) -> list[dict[str, str]]:
        endpoint = (self.config.azure_openai_endpoint or "").rstrip("/")
        api_key = self.config.azure_openai_api_key
        api_version = self.config.azure_openai_api_version
        if not (endpoint and api_key and api_version):
            return []

        url = f"{endpoint}/openai/deployments"
        params = {"api-version": api_version}
        headers = {"api-key": api_key}
        timeout = float(self.config.openai_timeout)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            payload: Any = response.json()

        if not isinstance(payload, dict):
            return []

        data = payload.get("data", [])
        if not isinstance(data, list):
            return []

        entries = [entry for item in data if (entry := _normalize_deployment_entry(item)) is not None]
        entries.sort(key=lambda item: item["id"])
        return entries

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
        """List runtime-selectable Azure deployment identities."""
        try:
            remote_entries = await self._fetch_remote_deployments()
        except Exception as error:  # noqa: BLE001
            logger.warning(
                "Azure deployment listing failed, falling back to configured metadata: %s",
                error,
            )
        else:
            if remote_entries:
                return remote_entries

        return self._configured_deployments()
