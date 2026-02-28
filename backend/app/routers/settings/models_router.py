"""
Models Router - Settings endpoints for LLM model management
Provides endpoints to list, get, and change the active LLM model.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.ai.ai_service import AIService, AIServiceManager
from app.services.ai.config import AIConfig
from app.services.ai.interfaces import ChatMessage
from app.services.models_service import ModelsService

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models
class PricingInfo(BaseModel):
    """Pricing information for a model."""

    input: float = Field(description="Input tokens price per 1K tokens")
    output: float = Field(description="Output tokens price per 1K tokens")
    currency: str = Field(description="Currency code (e.g., USD)")


class ModelResponse(BaseModel):
    """Model information response."""

    id: str = Field(description="Model ID")
    name: str = Field(description="Human-readable model name")
    context_window: int = Field(description="Maximum context window size")
    pricing: PricingInfo | None = Field(description="Pricing information if available")


class AvailableModelsResponse(BaseModel):
    """Response for available models list."""

    models: list[ModelResponse] = Field(description="List of available models")
    cached_at: datetime = Field(description="When models were cached/fetched")


class CurrentModelResponse(BaseModel):
    """Response for current active model."""

    model: str = Field(description="Current active model ID")


class SetModelRequest(BaseModel):
    """Request to change active model."""

    model_id: str = Field(description="Model ID to set as active")


class SetModelResponse(BaseModel):
    """Response after changing model."""

    success: bool = Field(description="Whether model was successfully changed")
    current_model: str = Field(description="Current active model ID")
    message: str | None = Field(default=None, description="Optional message")


# Endpoints
@router.get("/available-models", response_model=AvailableModelsResponse)
async def get_available_models(
    refresh: bool = Query(
        default=False, description="Force refresh from primary provider strategy, bypassing cache"
    )
) -> AvailableModelsResponse:
    """
    Get list of available models for the active provider strategy.

    OpenAI listings are cached to disk with a 7-day TTL. Use refresh=true to bypass cache.

    Args:
        refresh: Force refresh from API, ignoring cache

    Returns:
        List of available models with pricing information

    Raises:
        HTTPException: If failed to fetch models
    """
    try:
        models_service = ModelsService()
        models, cached_at = await models_service.get_available_models(
            force_refresh=refresh
        )

        response_models = [
            ModelResponse(
                id=m.id,
                name=m.name,
                context_window=m.context_window,
                pricing=PricingInfo(**m.pricing) if m.pricing else None,
            )
            for m in models
        ]

        logger.info(
            f"Returning {len(response_models)} models (cached_at={cached_at}, refresh={refresh})"
        )

        return AvailableModelsResponse(models=response_models, cached_at=cached_at)

    except Exception as e:
        logger.error(f"Failed to get available models: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch available models: {e!s}"
        ) from e


@router.get("/current-model", response_model=CurrentModelResponse)
async def get_current_model() -> CurrentModelResponse:
    """
    Get the currently active LLM model.

    Returns:
        Current model ID
    """
    try:
        ai_service = AIServiceManager.get_instance()
        current_model = ai_service.get_llm_model()

        logger.info(f"GET /current-model returning: {current_model}")
        logger.debug(f"AIService instance ID: {id(ai_service)}")

        return CurrentModelResponse(model=current_model)

    except Exception as e:
        logger.error(f"Failed to get current model: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get current model: {e!s}"
        ) from e


@router.put("/model", response_model=SetModelResponse)
async def set_model(request: SetModelRequest) -> SetModelResponse:
    """
    Change the active LLM model.

    This will reinitialize the AIService with the new model.
    All subsequent requests will use the new model.

    Args:
        request: Model ID to set

    Returns:
        Success status and current model

    Raises:
        HTTPException: If model change failed
    """
    try:
        model_id = request.model_id

        logger.info(f"PUT /model - Attempting to change model to: {model_id}")

        # Probe using the same provider logic used at runtime so endpoint/model
        # compatibility checks are identical during validation and inference.
        probe_config = AIConfig()
        if probe_config.llm_provider == "openai":
            probe_config.openai_llm_model = model_id

        probe_service = AIService(probe_config)
        try:
            await probe_service.chat(
                messages=[ChatMessage(role="user", content="Reply with: ok")],
                temperature=0,
                max_tokens=64,
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

        # Reinitialize AIService with new model
        logger.info(f"Calling reinitialize_with_model({model_id})")
        await AIServiceManager.reinitialize_with_model(model_id)
        logger.info("Reinitialization completed")

        # Verify change
        ai_service = AIServiceManager.get_instance()
        current_model = ai_service.get_llm_model()
        logger.info(f"Verification: AIService now reports model as {current_model}")
        logger.debug(f"AIService instance ID after reinit: {id(ai_service)}")

        if current_model == model_id:
            logger.info(f"✅ Successfully changed model to: {model_id}")
            return SetModelResponse(
                success=True,
                current_model=current_model,
                message=f"Model changed to {model_id}",
            )
        else:
            logger.error(
                f"❌ Model change verification failed: expected {model_id}, got {current_model}"
            )
            return SetModelResponse(
                success=False,
                current_model=current_model,
                message="Model change verification failed",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change model: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to change model: {e!s}"
        ) from e
