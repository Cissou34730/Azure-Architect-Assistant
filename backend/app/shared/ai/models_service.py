"""
Models Service - centralized provider-aware model listing and caching.

All providers use the same disk-cache mechanism:
- per-provider cache entries stored in a shared cache file
- shared TTL handling
- stale-cache fallback on fetch failure
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.shared.ai.ai_service import AIServiceManager
from app.shared.ai.config import AIConfig
from app.shared.config.app_settings import get_app_settings

logger = logging.getLogger(__name__)
MODEL_ID_DATE_LEN = 10
MODEL_ID_DOT_COUNT_FOR_DATE = 2


class ModelInfo:
    """Model information with pricing."""

    def __init__(
        self,
        id: str,
        name: str,
        context_window: int,
        pricing: dict[str, Any] | None = None,
    ):
        self.id = id
        self.name = name
        self.context_window = context_window
        self.pricing = pricing

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "context_window": self.context_window,
            "pricing": self.pricing,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelInfo":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            context_window=data["context_window"],
            pricing=data.get("pricing"),
        )


class ModelsService:
    """
    Service for managing available models with provider-aware strategy.

    Cache Strategy:
    - Shared disk cache for all providers
    - Per-provider/config cache keys inside one cache file
    - 7-day TTL by default
    - Manual refresh via force_refresh parameter
    """

    def __init__(self, cache_path: Path | None = None, config: AIConfig | None = None):
        """
        Initialize models service.

        Args:
            cache_path: Path to cache file (defaults to app settings)
        """
        app_settings = get_app_settings()

        self.cache_path = cache_path or app_settings.models_cache_path
        self.ttl_days = 7
        self.config = config or AIConfig.default()
        self.ai_service = None

        # Ensure cache directory exists
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"ModelsService initialized with cache at {self.cache_path}")

    async def get_available_models(
        self,
        force_refresh: bool = False,
        cache_only: bool = False,
    ) -> tuple[list[ModelInfo], datetime]:
        """
        Get available provider models using the centralized cache.

        Args:
            force_refresh: Force refresh from API, bypassing cache
            cache_only: Only use cache / configured fallback, do not perform live fetch

        Returns:
            Tuple of (models list, cached_at timestamp)
        """
        cache_key = self._cache_key()
        cached_entry = None if force_refresh else await self._load_cache_entry(cache_key)

        if cached_entry is not None:
            cached_at = datetime.fromisoformat(cached_entry["fetched_at"])
            age = datetime.now(timezone.utc) - cached_at
            if age <= timedelta(days=self.ttl_days):
                logger.info(
                    "Using cached models for %s (age: %s days)",
                    self.config.llm_provider,
                    age.days,
                )
                return [ModelInfo.from_dict(m) for m in cached_entry["models"]], cached_at
            logger.info(
                "Model cache expired for %s (age: %s days)",
                self.config.llm_provider,
                age.days,
            )

        if cache_only:
            logger.info("Cache-only model lookup for %s", self.config.llm_provider)
            models = await self._configured_fallback_models()
            return models, datetime.now(timezone.utc)

        return await self._fetch_and_cache(cache_key=cache_key, stale_entry=cached_entry)

    async def _fetch_and_cache(
        self,
        *,
        cache_key: str,
        stale_entry: dict[str, Any] | None,
    ) -> tuple[list[ModelInfo], datetime]:
        try:
            models = await self._fetch_models_for_provider()
            now = datetime.now(timezone.utc)
            await self._save_cache_entry(cache_key, models, now)
            return models, now
        except Exception as e:
            logger.error(
                "Failed to fetch models for provider %s: %s",
                self.config.llm_provider,
                e,
            )
            if stale_entry:
                logger.warning("Returning stale cache for provider %s", self.config.llm_provider)
                models = [ModelInfo.from_dict(m) for m in stale_entry["models"]]
                cached_at = datetime.fromisoformat(stale_entry["fetched_at"])
                return models, cached_at

            models = await self._configured_fallback_models()
            if models:
                logger.warning(
                    "Using configured fallback model list for provider %s",
                    self.config.llm_provider,
                )
                return models, datetime.now(timezone.utc)
            raise

    async def _fetch_models_for_provider(self) -> list[ModelInfo]:
        if self.config.llm_provider in {"copilot", "foundry"}:
            return await self._fetch_provider_models()
        return await self._fetch_from_openai()

    async def _fetch_from_openai(self) -> list[ModelInfo]:
        """
        Fetch models from OpenAI API and filter chat models.

        Returns:
            List of ModelInfo objects
        """
        logger.info("Fetching models from OpenAI API")
        runtime_models = await (await self._get_ai_service()).list_llm_runtime_models()
        logger.info("Found %d runtime models via AIService", len(runtime_models))

        # Convert to ModelInfo with pricing extraction
        model_infos = []
        models_with_pricing = 0
        models_without_pricing = 0

        for model in runtime_models:
            model_id = model["id"]
            # Extract context window from model metadata if available
            context_window = self._extract_context_window(model_id)

            # Pricing information (OpenAI API doesn't provide this directly)
            pricing = self._extract_pricing(model_id)

            if pricing:
                models_with_pricing += 1
            else:
                models_without_pricing += 1

            model_info = ModelInfo(
                id=model_id,
                name=self._format_model_name(model_id),
                context_window=context_window,
                pricing=pricing,
            )
            model_infos.append(model_info)

        logger.info(
            f"Models with pricing: {models_with_pricing}, "
            f"without pricing: {models_without_pricing}"
        )

        # Sort by model ID for consistent ordering
        model_infos.sort(key=lambda m: m.id, reverse=True)

        return model_infos

    async def _fetch_provider_models(self) -> list[ModelInfo]:
        runtime_models = await (await self._get_ai_service()).list_llm_runtime_models()
        model_infos: list[ModelInfo] = []
        for model in runtime_models:
            model_id = str(model["id"])
            raw_context_window = model.get("context_window")
            if isinstance(raw_context_window, str) and raw_context_window.isdigit():
                context_window = int(raw_context_window)
            elif isinstance(raw_context_window, int):
                context_window = raw_context_window
            else:
                context_window = self._extract_context_window(model_id)
            model_infos.append(
                ModelInfo(
                    id=model_id,
                    name=str(model.get("name") or model.get("model") or model_id),
                    context_window=context_window,
                    pricing=None,
                )
            )
        return model_infos

    async def _configured_fallback_models(self) -> list[ModelInfo]:
        if self.config.llm_provider == "foundry" and self.config.foundry_model:
            return [
                ModelInfo(
                    id=self.config.foundry_model,
                    name=self.config.foundry_model,
                    context_window=self._extract_context_window(self.config.foundry_model),
                    pricing=None,
                )
            ]
        if self.config.llm_provider == "copilot":
            allowed = [
                item.strip()
                for item in self.config.copilot_allowed_models.split(",")
                if item.strip()
            ]
            if self.config.copilot_default_model and self.config.copilot_default_model not in allowed:
                allowed.insert(0, self.config.copilot_default_model)
            return [
                ModelInfo(
                    id=model_id,
                    name=model_id,
                    context_window=self._extract_context_window(model_id),
                    pricing=None,
                )
                for model_id in allowed
            ]
        return []

    def _extract_context_window(self, model_id: str) -> int:  # noqa: PLR0911
        """
        Extract context window size based on model ID.

        This is a lookup table since OpenAI API doesn't provide this.
        """
        context_windows = {
            # GPT-4o models (2024+)
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-4o-2024-11-20": 128000,
            "gpt-4o-2024-08-06": 128000,
            "gpt-4o-2024-05-13": 128000,
            "gpt-4o-mini-2024-07-18": 128000,
            # O1 models (reasoning)
            "o1": 200000,
            "o1-mini": 128000,
            "o1-preview": 128000,
            "o1-2024-12-17": 200000,
            "o1-mini-2024-09-12": 128000,
            "o1-preview-2024-09-12": 128000,
            # GPT-4 Turbo models
            "gpt-4-turbo": 128000,
            "gpt-4-turbo-preview": 128000,
            "gpt-4-1106-preview": 128000,
            "gpt-4-0125-preview": 128000,
            "gpt-4-turbo-2024-04-09": 128000,
            # GPT-4 base models
            "gpt-4": 8192,
            "gpt-4-0613": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-32k-0613": 32768,
            # GPT-3.5 Turbo models
            "gpt-3.5-turbo": 16385,
            "gpt-3.5-turbo-16k": 16385,
            "gpt-3.5-turbo-1106": 16385,
            "gpt-3.5-turbo-0125": 16385,
        }

        # Exact match
        if model_id in context_windows:
            return context_windows[model_id]

        # Prefix match for variants
        for prefix, window in context_windows.items():
            if model_id.startswith(prefix):
                return window

        # Default fallback based on model family
        if "o1" in model_id:
            return 128000
        if "gpt-4o" in model_id:
            return 128000
        if "gpt-4" in model_id and "32k" in model_id:
            return 32768
        if "gpt-4" in model_id:
            return 8192
        if "gpt-3.5" in model_id:
            return 16385

        # Ultimate fallback
        return 8192

    def _extract_pricing(self, model_id: str) -> dict[str, Any] | None:  # noqa: C901, PLR0911, PLR0912
        """
        Extract pricing information based on model ID.

        This is a lookup table of current OpenAI pricing (as of Feb 2025).
        Prices are per 1K tokens in USD.
        """
        pricing_table = {
            # GPT-4o models (latest, most capable)
            "gpt-4o": {"input": 0.0025, "output": 0.01, "currency": "USD"},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006, "currency": "USD"},
            "gpt-4o-2024-11-20": {"input": 0.0025, "output": 0.01, "currency": "USD"},
            "gpt-4o-2024-08-06": {"input": 0.0025, "output": 0.01, "currency": "USD"},
            "gpt-4o-2024-05-13": {"input": 0.005, "output": 0.015, "currency": "USD"},
            "gpt-4o-mini-2024-07-18": {"input": 0.00015, "output": 0.0006, "currency": "USD"},
            # O1 models (reasoning models)
            "o1": {"input": 0.015, "output": 0.06, "currency": "USD"},
            "o1-mini": {"input": 0.003, "output": 0.012, "currency": "USD"},
            "o1-preview": {"input": 0.015, "output": 0.06, "currency": "USD"},
            "o1-2024-12-17": {"input": 0.015, "output": 0.06, "currency": "USD"},
            "o1-mini-2024-09-12": {"input": 0.003, "output": 0.012, "currency": "USD"},
            "o1-preview-2024-09-12": {"input": 0.015, "output": 0.06, "currency": "USD"},
            # GPT-4 Turbo models
            "gpt-4-turbo": {"input": 0.01, "output": 0.03, "currency": "USD"},
            "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03, "currency": "USD"},
            "gpt-4-1106-preview": {"input": 0.01, "output": 0.03, "currency": "USD"},
            "gpt-4-0125-preview": {"input": 0.01, "output": 0.03, "currency": "USD"},
            "gpt-4-turbo-2024-04-09": {"input": 0.01, "output": 0.03, "currency": "USD"},
            # GPT-4 base models
            "gpt-4": {"input": 0.03, "output": 0.06, "currency": "USD"},
            "gpt-4-0613": {"input": 0.03, "output": 0.06, "currency": "USD"},
            "gpt-4-32k": {"input": 0.06, "output": 0.12, "currency": "USD"},
            "gpt-4-32k-0613": {"input": 0.06, "output": 0.12, "currency": "USD"},
            # GPT-3.5 Turbo models
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015, "currency": "USD"},
            "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004, "currency": "USD"},
            "gpt-3.5-turbo-1106": {"input": 0.001, "output": 0.002, "currency": "USD"},
            "gpt-3.5-turbo-0125": {"input": 0.0005, "output": 0.0015, "currency": "USD"},
        }

        # Exact match
        if model_id in pricing_table:
            return pricing_table[model_id]

        # Prefix match for variants
        for prefix, pricing in pricing_table.items():
            if model_id.startswith(prefix):
                return pricing

        # Fallback estimates based on model family patterns
        model_lower = model_id.lower()

        # GPT-4o family
        if "gpt-4o-mini" in model_lower or "gpt4o-mini" in model_lower:
            logger.debug(f"Using GPT-4o Mini fallback pricing for {model_id}")
            return {"input": 0.00015, "output": 0.0006, "currency": "USD"}
        if "gpt-4o" in model_lower or "gpt4o" in model_lower:
            logger.debug(f"Using GPT-4o fallback pricing for {model_id}")
            return {"input": 0.0025, "output": 0.01, "currency": "USD"}

        # O1 family
        if "o1-mini" in model_lower:
            logger.debug(f"Using O1 Mini fallback pricing for {model_id}")
            return {"input": 0.003, "output": 0.012, "currency": "USD"}
        if "o1" in model_lower or "o3" in model_lower:
            logger.debug(f"Using O1/O3 fallback pricing for {model_id}")
            return {"input": 0.015, "output": 0.06, "currency": "USD"}

        # GPT-4 Turbo family
        if "gpt-4-turbo" in model_lower or "gpt4-turbo" in model_lower:
            logger.debug(f"Using GPT-4 Turbo fallback pricing for {model_id}")
            return {"input": 0.01, "output": 0.03, "currency": "USD"}

        # GPT-4 32k
        if "gpt-4" in model_lower and "32k" in model_lower:
            logger.debug(f"Using GPT-4 32k fallback pricing for {model_id}")
            return {"input": 0.06, "output": 0.12, "currency": "USD"}

        # GPT-4 base
        if "gpt-4" in model_lower or "gpt4" in model_lower:
            logger.debug(f"Using GPT-4 fallback pricing for {model_id}")
            return {"input": 0.03, "output": 0.06, "currency": "USD"}

        # GPT-3.5 Turbo family
        if "gpt-3.5" in model_lower or "gpt3.5" in model_lower:
            logger.debug(f"Using GPT-3.5 fallback pricing for {model_id}")
            return {"input": 0.0005, "output": 0.0015, "currency": "USD"}

        # No pricing available for this model
        logger.warning(f"No pricing information available for model: {model_id}")
        return None

    def _format_model_name(self, model_id: str) -> str:
        """
        Format model ID into human-readable name.

        Examples:
        - gpt-4o -> GPT-4o
        - gpt-4o-mini -> GPT-4o Mini
        - gpt-4-turbo-preview -> GPT-4 Turbo Preview
        - o1-preview -> O1 Preview
        - gpt-3.5-turbo-1106 -> GPT-3.5 Turbo (1106)
        """
        # Special handling for O1 models
        if model_id.startswith("o1"):
            name = model_id.replace("-", " ").replace("o1", "O1")
            return " ".join(word.capitalize() for word in name.split())

        # Replace hyphens with spaces
        name = model_id.replace("-", " ")

        # Capitalize GPT prefix and handle version numbers
        if name.startswith("gpt "):
            # Handle "gpt 4o" -> "GPT-4o"
            if "4o" in name:
                name = name.replace("gpt 4o", "GPT-4o")
            elif "3.5" in name:
                name = name.replace("gpt 3.5", "GPT-3.5")
            elif "gpt 4" in name:
                name = name.replace("gpt 4", "GPT-4")
            elif "gpt 3" in name:
                name = name.replace("gpt 3", "GPT-3")
            else:
                name = name.replace("gpt ", "GPT-")

        # Capitalize words (but preserve version numbers and dates)
        parts = name.split()
        formatted_parts = []
        for part in parts:
            # Keep dates and version numbers as-is
            if part.isdigit() or (
                len(part) == MODEL_ID_DATE_LEN
                and part.count(".") == MODEL_ID_DOT_COUNT_FOR_DATE
            ):
                formatted_parts.append(f"({part})")
            else:
                formatted_parts.append(part.capitalize())

        return " ".join(formatted_parts)

    async def _get_ai_service(self):
        if self.ai_service is None:
            self.ai_service = AIServiceManager.create_probe(self.config)
        return self.ai_service

    def _cache_key(self) -> str:
        provider = self.config.llm_provider
        if provider == "foundry":
            raw = "|".join(
                [
                    provider,
                    self.config.foundry_endpoint,
                    self.config.foundry_resource_id,
                    self.config.foundry_model,
                ]
            )
        elif provider == "copilot":
            raw = "|".join(
                [
                    provider,
                    self.config.copilot_default_model,
                    self.config.copilot_allowed_models,
                ]
            )
        else:
            raw = "|".join([provider, self.config.openai_llm_model])
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return f"{provider}:{digest}"

    async def _load_cache_document(self) -> dict[str, Any] | None:
        if not self.cache_path.exists():
            return None

        try:
            content = await asyncio.to_thread(self.cache_path.read_text, encoding="utf-8")
            data = json.loads(content)
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load cache from disk: {e}")
            return None

    def _load_legacy_cache_entry(self, data: dict[str, Any]) -> dict[str, Any] | None:
        if "models" not in data or "fetched_at" not in data:
            return None
        provider = data.get("provider", "openai")
        if provider == self.config.llm_provider:
            return data
        return None

    async def _load_cache_entry(self, cache_key: str) -> dict[str, Any] | None:
        data = await self._load_cache_document()
        if data is None:
            return None

        # Backward compatibility for the old single-entry OpenAI cache schema.
        legacy_entry = self._load_legacy_cache_entry(data)
        if legacy_entry is not None or ("models" in data and "fetched_at" in data):
            return legacy_entry

        entries = data.get("entries")
        if not isinstance(entries, dict):
            logger.warning("Invalid models cache schema, ignoring")
            return None

        entry = entries.get(cache_key)
        if not isinstance(entry, dict):
            return None
        if "models" in entry and "fetched_at" in entry:
            return entry
        logger.warning("Invalid cache entry schema for %s", cache_key)
        return None

    async def _save_cache_entry(
        self,
        cache_key: str,
        models: list[ModelInfo],
        timestamp: datetime,
    ) -> None:
        existing = await self._load_cache_document()
        if not isinstance(existing, dict) or "entries" not in existing:
            existing = {"entries": {}}

        entries = existing.get("entries")
        if not isinstance(entries, dict):
            entries = {}
            existing["entries"] = entries

        entries[cache_key] = {
            "provider": self.config.llm_provider,
            "models": [m.to_dict() for m in models],
            "fetched_at": timestamp.isoformat(),
            "ttl_days": self.ttl_days,
        }

        temp_path = self.cache_path.with_suffix(".tmp")

        try:
            content = json.dumps(existing, indent=2)
            await asyncio.to_thread(temp_path.write_text, content, encoding="utf-8")
            await asyncio.to_thread(temp_path.replace, self.cache_path)
            logger.info(
                "Cached %d models for %s to %s",
                len(models),
                self.config.llm_provider,
                self.cache_path,
            )
        except OSError as e:
            logger.error(f"Failed to save cache to disk: {e}")
            if temp_path.exists():
                await asyncio.to_thread(temp_path.unlink)
            raise
