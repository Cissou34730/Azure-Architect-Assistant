"""Service layer for settings/models router operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException

from app.core.app_settings import get_app_settings
from app.services.ai.ai_service import AIServiceManager
from app.services.ai.config import AIConfig
from app.services.ai.interfaces import ChatMessage
from app.services.models_service import ModelsService


class SettingsModelsService:
    """Coordinates model listing, current model lookup, and model switching."""

    async def get_available_models(
        self, *, refresh: bool
    ) -> tuple[list[dict[str, Any]], datetime]:
        models_service = ModelsService()
        models, cached_at = await models_service.get_available_models(
            force_refresh=refresh
        )
        payload = [
            {
                "id": m.id,
                "name": m.name,
                "context_window": m.context_window,
                "pricing": m.pricing,
            }
            for m in models
        ]
        return payload, cached_at

    def get_current_model(self) -> str:
        ai_service = AIServiceManager.get_instance()
        return ai_service.get_llm_model()

    async def set_model(self, *, model_id: str) -> dict[str, Any]:
        base_probe_config = AIConfig.default()
        if base_probe_config.llm_provider == "azure":
            probe_config = base_probe_config.model_copy(
                update={"azure_llm_deployment": model_id}
            )
        else:
            probe_config = base_probe_config.model_copy(
                update={"openai_llm_model": model_id}
            )

        probe_service = AIServiceManager.create_probe(probe_config)
        _s = get_app_settings()
        try:
            await probe_service.chat(
                messages=[ChatMessage(role="user", content="Reply with: ok")],
                temperature=_s.models_probe_temperature,
                max_tokens=_s.models_probe_max_tokens,
                timeout=20.0,
            )
        except Exception as probe_error:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Model '{model_id}' is not usable with current provider compatibility strategy: "
                    f"{probe_error}"
                ),
            ) from probe_error

        await AIServiceManager.reinitialize_with_model(model_id)
        current_model = self.get_current_model()

        return {
            "success": current_model == model_id,
            "current_model": current_model,
            "message": (
                f"Model changed to {model_id}"
                if current_model == model_id
                else "Model change verification failed"
            ),
        }

