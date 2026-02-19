"""
Models Service - Disk-Cached OpenAI Models Management
Fetches and caches available OpenAI chat completion models with 7-day TTL.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from app.core.app_settings import get_app_settings, get_openai_settings

logger = logging.getLogger(__name__)


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
    Service for managing OpenAI models with disk-based caching.
    
    Cache Strategy:
    - Fetch from OpenAI API on first request
    - Persist to disk (backend/data/openai_models_cache.json)
    - Reload from disk on subsequent requests
    - 7-day TTL - re-fetch if cache expired
    - Manual refresh via force_refresh parameter
    """

    def __init__(self, cache_path: Path | None = None):
        """
        Initialize models service.

        Args:
            cache_path: Path to cache file (defaults to app settings)
        """
        app_settings = get_app_settings()
        openai_settings = get_openai_settings()

        self.cache_path = cache_path or app_settings.models_cache_path
        self.ttl_days = 7
        self.client = AsyncOpenAI(api_key=openai_settings.api_key)

        # Ensure cache directory exists
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"ModelsService initialized with cache at {self.cache_path}")

    async def get_available_models(
        self, force_refresh: bool = False
    ) -> tuple[list[ModelInfo], datetime]:
        """
        Get available OpenAI chat completion models.
        
        Checks disk cache → TTL → fetches from API if needed.

        Args:
            force_refresh: Force refresh from API, bypassing cache

        Returns:
            Tuple of (models list, cached_at timestamp)
        """
        if force_refresh:
            logger.info("Force refresh requested, bypassing cache")
            return await self._fetch_and_cache()

        # Try loading from disk
        cached_data = await self._load_from_disk()

        if cached_data is None:
            logger.info("No cache found, fetching from OpenAI API")
            return await self._fetch_and_cache()

        # Check TTL
        cached_at = datetime.fromisoformat(cached_data["fetched_at"])
        age = datetime.now(timezone.utc) - cached_at

        if age > timedelta(days=self.ttl_days):
            logger.info(f"Cache expired (age: {age.days} days), fetching fresh data")
            return await self._fetch_and_cache()

        logger.info(f"Using cached models (age: {age.days} days)")
        models = [ModelInfo.from_dict(m) for m in cached_data["models"]]
        return models, cached_at

    async def _fetch_and_cache(self) -> tuple[list[ModelInfo], datetime]:
        """
        Fetch models from OpenAI API and cache to disk.

        Returns:
            Tuple of (models list, fetched_at timestamp)
        """
        try:
            models = await self._fetch_from_openai()
            now = datetime.now(timezone.utc)

            await self._save_to_disk(models, now)

            return models, now

        except Exception as e:
            logger.error(f"Failed to fetch models from OpenAI: {e}")
            # Try to return stale cache if available
            cached_data = await self._load_from_disk()
            if cached_data:
                logger.warning("Returning stale cache due to API error")
                models = [ModelInfo.from_dict(m) for m in cached_data["models"]]
                cached_at = datetime.fromisoformat(cached_data["fetched_at"])
                return models, cached_at
            raise

    async def _fetch_from_openai(self) -> list[ModelInfo]:
        """
        Fetch models from OpenAI API and filter chat models.

        Returns:
            List of ModelInfo objects
        """
        logger.info("Fetching models from OpenAI API")

        # Fetch all models
        response = await self.client.models.list()
        all_models = list(response.data)

        # Only exclude known non-chat model types
        # Be permissive - include everything except models we know are NOT for chat
        excluded_prefixes = (
            "text-embedding",    # Embedding models
            "text-similarity",   # Similarity models
            "text-search",       # Search models
            "whisper",           # Audio transcription
            "dall-e",            # Image generation
            "tts",               # Text-to-speech
            "text-davinci-edit", # Edit models (deprecated)
            "text-moderation",   # Moderation models
            "davinci-",          # Legacy completion models
            "curie-",            # Legacy completion models
            "babbage-",          # Legacy completion models
            "ada-",              # Legacy completion models
        )
        
        chat_models = [
            model
            for model in all_models
            if not model.id.startswith(excluded_prefixes)
        ]

        logger.info(f"Found {len(chat_models)} chat models out of {len(all_models)} total")

        # Convert to ModelInfo with pricing extraction
        model_infos = []
        models_with_pricing = 0
        models_without_pricing = 0
        
        for model in chat_models:
            # Extract context window from model metadata if available
            context_window = self._extract_context_window(model.id)

            # Pricing information (OpenAI API doesn't provide this directly)
            pricing = self._extract_pricing(model.id)
            
            if pricing:
                models_with_pricing += 1
            else:
                models_without_pricing += 1

            model_info = ModelInfo(
                id=model.id,
                name=self._format_model_name(model.id),
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

    def _extract_context_window(self, model_id: str) -> int:
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

    def _extract_pricing(self, model_id: str) -> dict[str, Any] | None:
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
            if part.isdigit() or (len(part) == 10 and part.count(".") == 2):
                formatted_parts.append(f"({part})")
            # Keep version-like strings in parentheses
            elif part.isdigit() or (len(part) >= 4 and part.isdigit()):
                formatted_parts.append(f"({part})")
            else:
                formatted_parts.append(part.capitalize())

        return " ".join(formatted_parts)

    async def _load_from_disk(self) -> dict[str, Any] | None:
        """
        Load cached models from disk.

        Returns:
            Cache data dictionary or None if not found/invalid
        """
        if not self.cache_path.exists():
            return None

        try:
            # Use asyncio.to_thread for async file I/O without aiofiles dependency
            content = await asyncio.to_thread(self.cache_path.read_text, encoding="utf-8")
            data = json.loads(content)

            # Validate schema
            if "models" not in data or "fetched_at" not in data:
                logger.warning("Invalid cache schema, ignoring")
                return None

            return data

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load cache from disk: {e}")
            return None

    async def _save_to_disk(self, models: list[ModelInfo], timestamp: datetime) -> None:
        """
        Save models to disk cache with atomic write.

        Args:
            models: List of ModelInfo objects
            timestamp: Fetch timestamp
        """
        cache_data = {
            "models": [m.to_dict() for m in models],
            "fetched_at": timestamp.isoformat(),
            "ttl_days": self.ttl_days,
        }

        # Atomic write: write to temp file, then rename
        temp_path = self.cache_path.with_suffix(".tmp")

        try:
            # Use asyncio.to_thread for async file I/O
            content = json.dumps(cache_data, indent=2)
            await asyncio.to_thread(temp_path.write_text, content, encoding="utf-8")

            # Atomic replace
            await asyncio.to_thread(temp_path.replace, self.cache_path)

            logger.info(f"Cached {len(models)} models to {self.cache_path}")

        except OSError as e:
            logger.error(f"Failed to save cache to disk: {e}")
            # Clean up temp file if it exists
            if temp_path.exists():
                await asyncio.to_thread(temp_path.unlink)
            raise
