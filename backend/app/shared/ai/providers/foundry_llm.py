"""AI Foundry LLM provider implementation."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import AIConfig
from .foundry_client import get_foundry_client
from .openai_llm import OpenAILLMProvider

logger = logging.getLogger(__name__)

_MANAGEMENT_API_VERSION = "2024-10-01"

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


def _is_embedding_model(model_name: str) -> bool:
    return model_name.lower().startswith("text-embedding")


def _is_excluded_model(model_name: str) -> bool:
    lower = model_name.lower()
    return any(lower.startswith(prefix) for prefix in _EXCLUDED_MODEL_PREFIXES)


def _sort_deployments(items: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(items, key=lambda item: item["id"])


def _normalize_management_deployment(item: object) -> dict[str, str] | None:
    if not isinstance(item, dict):
        return None

    properties = item.get("properties")
    if not isinstance(properties, dict):
        return None
    if str(properties.get("provisioningState", "")).lower() != "succeeded":
        return None

    deployment_id = item.get("name") or item.get("id")
    if not isinstance(deployment_id, str) or not deployment_id.strip():
        return None

    model_info = properties.get("model")
    model_name = deployment_id.strip()
    model_format = "unknown"
    if isinstance(model_info, dict):
        if isinstance(model_info.get("name"), str) and model_info["name"].strip():
            model_name = model_info["name"].strip()
        if isinstance(model_info.get("format"), str) and model_info["format"].strip():
            model_format = model_info["format"].strip()

    return {
        "id": deployment_id.strip(),
        "model": model_name,
        "format": model_format,
    }


def _normalize_data_plane_deployment(item: object) -> dict[str, str] | None:
    if not isinstance(item, dict):
        return None
    if str(item.get("status", "")).lower() != "succeeded":
        return None

    deployment_id = item.get("id")
    if not isinstance(deployment_id, str) or not deployment_id.strip():
        return None

    model_name = item.get("model")
    normalized_model = model_name.strip() if isinstance(model_name, str) and model_name.strip() else deployment_id.strip()
    return {
        "id": deployment_id.strip(),
        "model": normalized_model,
        "format": "unknown",
    }


async def discover_foundry_deployments(config: AIConfig) -> list[dict[str, str]]:
    """Discover AI Foundry deployments via management plane with data-plane fallback."""
    endpoint = (config.foundry_endpoint or "").rstrip("/")
    api_key = config.foundry_api_key
    resource_id = (config.foundry_resource_id or "").strip()
    if not (endpoint and api_key):
        return []

    timeout = min(5.0, float(config.openai_timeout))

    if resource_id:
        management_url = f"https://management.azure.com{resource_id.rstrip('/')}/deployments"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    management_url,
                    params={"api-version": _MANAGEMENT_API_VERSION},
                    headers={"api-key": api_key},
                )
        except Exception as exc:
            logger.warning("AI Foundry management-plane discovery failed: %s", exc)
        else:
            if response.status_code == 401:
                logger.info("AI Foundry management-plane discovery rejected api-key auth; falling back to data plane")
            else:
                try:
                    response.raise_for_status()
                except Exception as exc:
                    logger.warning("AI Foundry management-plane discovery failed: %s", exc)
                else:
                    deployments = [
                        deployment
                        for item in response.json().get("value", [])
                        if (deployment := _normalize_management_deployment(item)) is not None
                    ]
                    return _sort_deployments(deployments)

    data_plane_url = f"{endpoint}/openai/deployments"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                data_plane_url,
                params={"api-version": config.foundry_api_version},
                headers={"api-key": api_key},
            )
            response.raise_for_status()
    except Exception as exc:
        logger.warning("AI Foundry data-plane discovery failed: %s", exc)
        return []

    deployments = [
        deployment
        for item in response.json().get("data", [])
        if (deployment := _normalize_data_plane_deployment(item)) is not None
    ]
    return _sort_deployments(deployments)


class FoundryLLMProvider(OpenAILLMProvider):
    """AI Foundry implementation of the LLM provider."""

    def __init__(self, config: AIConfig):
        self.config = config
        self.client = get_foundry_client(config)
        self.model = config.foundry_model
        logger.info("AI Foundry LLM Provider initialized with deployment: %s", self.model)

    async def list_runtime_models(self) -> list[dict[str, str]]:
        deployments = await discover_foundry_deployments(self.config)
        return [
            deployment
            for deployment in deployments
            if not _is_excluded_model(deployment["model"])
        ]
