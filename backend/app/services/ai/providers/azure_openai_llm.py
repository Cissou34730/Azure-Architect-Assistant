"""
Azure OpenAI LLM Provider Implementation.
"""

import logging

import httpx

from ..config import AIConfig
from .azure_openai_client import get_azure_openai_client
from .openai_llm import OpenAILLMProvider

logger = logging.getLogger(__name__)


class AzureOpenAILLMProvider(OpenAILLMProvider):
    """Azure OpenAI implementation of LLM provider."""

    def __init__(self, config: AIConfig):
        self.config = config
        self.client = get_azure_openai_client(config)
        self.model = config.azure_llm_deployment
        logger.info("Azure OpenAI LLM Provider initialized with deployment: %s", self.model)

    async def list_runtime_models(self) -> list[dict[str, str]]:
        """List runtime-selectable Azure deployment identities."""
        endpoint = (self.config.azure_openai_endpoint or "").rstrip("/")
        api_key = self.config.azure_openai_api_key
        api_version = self.config.azure_openai_api_version

        if endpoint and api_key and api_version:
            url = f"{endpoint}/openai/deployments"
            params = {"api-version": api_version}
            headers = {"api-key": api_key}

            try:
                timeout = float(self.config.openai_timeout)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(url, params=params, headers=headers)
                    response.raise_for_status()
                    payload = response.json()

                data = payload.get("data", []) if isinstance(payload, dict) else []
                if isinstance(data, list):
                    entries: list[dict[str, str]] = []
                    for item in data:
                        if not isinstance(item, dict):
                            continue
                        deployment = item.get("id")
                        model_name = item.get("model") or ""
                        if not isinstance(deployment, str) or not deployment.strip():
                            continue
                        lower_model = model_name.lower() if isinstance(model_name, str) else ""
                        if lower_model.startswith("text-embedding"):
                            continue
                        entries.append(
                            {
                                "id": deployment.strip(),
                                "model": model_name.strip() if isinstance(model_name, str) and model_name.strip() else deployment.strip(),
                            }
                        )

                    entries.sort(key=lambda item: item["id"])
                    if entries:
                        return entries
            except Exception as error:  # noqa: BLE001
                logger.warning(
                    "Azure deployment listing failed, falling back to configured metadata: %s",
                    error,
                )

        deployments: list[str] = []
        if self.config.azure_llm_deployment:
            deployments.append(self.config.azure_llm_deployment)
        if self.config.azure_llm_deployments:
            deployments.extend(
                [item.strip() for item in self.config.azure_llm_deployments.split(",") if item.strip()]
            )

        unique_deployments: list[str] = []
        seen: set[str] = set()
        for deployment in deployments:
            if deployment not in seen:
                seen.add(deployment)
                unique_deployments.append(deployment)

        return [{"id": deployment, "model": deployment} for deployment in unique_deployments]
