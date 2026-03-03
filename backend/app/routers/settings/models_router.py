"""
Models Router - Settings endpoints for LLM model management
Provides endpoints to list, get, and change the active LLM model.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.routers.error_utils import internal_server_error
from app.services.settings_models_service import SettingsModelsService

logger = logging.getLogger(__name__)

router = APIRouter()
settings_models_service = SettingsModelsService()


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
        models, cached_at = await settings_models_service.get_available_models(
            refresh=refresh
        )

        response_models = []
        for model in models:
            pricing = model.get("pricing")
            response_models.append(
                ModelResponse(
                    id=str(model["id"]),
                    name=str(model["name"]),
                    context_window=int(model["context_window"]),
                    pricing=PricingInfo(**pricing) if isinstance(pricing, dict) else None,
                )
            )

        logger.info(
            f"Returning {len(response_models)} models (cached_at={cached_at}, refresh={refresh})"
        )

        return AvailableModelsResponse(models=response_models, cached_at=cached_at)

    except Exception as e:
        raise internal_server_error(
            logger=logger,
            message=f"Failed to get available models: {e}",
            exc=e,
            detail_prefix="Failed to fetch available models",
        ) from e


@router.get("/current-model", response_model=CurrentModelResponse)
async def get_current_model() -> CurrentModelResponse:
    """
    Get the currently active LLM model.

    Returns:
        Current model ID
    """
    try:
        current_model = settings_models_service.get_current_model()

        logger.info(f"GET /current-model returning: {current_model}")

        return CurrentModelResponse(model=current_model)

    except Exception as e:
        raise internal_server_error(
            logger=logger,
            message=f"Failed to get current model: {e}",
            exc=e,
            detail_prefix="Failed to get current model",
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
        payload = await settings_models_service.set_model(model_id=model_id)
        return SetModelResponse.model_validate(payload)

    except HTTPException:
        raise
    except Exception as e:
        raise internal_server_error(
            logger=logger,
            message=f"Failed to change model: {e}",
            exc=e,
            detail_prefix="Failed to change model",
        ) from e
