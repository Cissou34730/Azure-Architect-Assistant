"""Provider-aware settings endpoints for LLM runtime management."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.features.settings.application.architect_profile_service import ArchitectProfileService
from app.features.settings.application.settings_service import SettingsModelsService
from app.features.settings.contracts import ArchitectProfileResponseContract
from app.features.settings.domain.architect_profile import ArchitectProfile
from app.shared.db.projects_database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

_settings_models_service = SettingsModelsService()
_architect_profile_service = ArchitectProfileService()


def get_settings_models_service_dep() -> SettingsModelsService:
    return _settings_models_service


def get_architect_profile_service_dep() -> ArchitectProfileService:
    return _architect_profile_service


class PricingInfo(BaseModel):
    input: float = Field(description="Input tokens price per 1K tokens")
    output: float = Field(description="Output tokens price per 1K tokens")
    currency: str = Field(description="Currency code")


class ModelResponse(BaseModel):
    id: str
    name: str
    context_window: int
    pricing: PricingInfo | None = None


class AvailableModelsResponse(BaseModel):
    models: list[ModelResponse]
    cached_at: datetime


class CurrentModelResponse(BaseModel):
    model: str


class CurrentProviderResponse(BaseModel):
    provider: str


class SetModelRequest(BaseModel):
    model_id: str


class SetModelResponse(BaseModel):
    success: bool
    current_model: str
    current_provider: str | None = None
    message: str | None = None


class ProviderAuthResponse(BaseModel):
    available: bool
    authenticated: bool
    state: str
    login: str | None = None
    auth_type: str | None = None
    host: str | None = None
    status_message: str | None = None
    cli_path: str | None = None
    quota: dict[str, Any] | None = None


class ProviderResponse(BaseModel):
    id: str
    name: str
    status: str
    status_message: str | None = None
    selected: bool
    models: list[ModelResponse]
    auth: ProviderAuthResponse | None = None


class LLMOptionsResponse(BaseModel):
    active_provider: str
    active_model: str
    providers: list[ProviderResponse]


class LLMSelectionRequest(BaseModel):
    provider_id: str
    model_id: str


class CopilotActionResponse(BaseModel):
    success: bool = True
    launched: bool | None = None
    manual_logout_required: bool | None = None
    message: str


def _serialize_models(models: list[dict[str, Any]]) -> list[ModelResponse]:
    response_models: list[ModelResponse] = []
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
    return response_models


@router.get("/available-models", response_model=AvailableModelsResponse)
async def get_available_models(
    refresh: bool = Query(default=False),
    settings_models_service: SettingsModelsService = Depends(get_settings_models_service_dep),
) -> AvailableModelsResponse:
    models, cached_at = await settings_models_service.get_available_models(refresh=refresh)
    return AvailableModelsResponse(models=_serialize_models(models), cached_at=cached_at)


@router.get("/current-model", response_model=CurrentModelResponse)
async def get_current_model(
    settings_models_service: SettingsModelsService = Depends(get_settings_models_service_dep),
) -> CurrentModelResponse:
    return CurrentModelResponse(model=settings_models_service.get_current_model())


@router.get("/current-provider", response_model=CurrentProviderResponse)
async def get_current_provider(
    settings_models_service: SettingsModelsService = Depends(get_settings_models_service_dep),
) -> CurrentProviderResponse:
    return CurrentProviderResponse(provider=settings_models_service.get_current_provider())


@router.put("/model", response_model=SetModelResponse)
async def set_model(
    request: SetModelRequest,
    settings_models_service: SettingsModelsService = Depends(get_settings_models_service_dep),
) -> SetModelResponse:
    payload = await settings_models_service.set_model(model_id=request.model_id)
    return SetModelResponse.model_validate(payload)


@router.get("/llm-options", response_model=LLMOptionsResponse)
async def get_llm_options(
    refresh: bool = Query(default=False),
    settings_models_service: SettingsModelsService = Depends(get_settings_models_service_dep),
) -> LLMOptionsResponse:
    payload = await settings_models_service.get_llm_options(refresh=refresh)
    providers = []
    for provider in payload["providers"]:
        providers.append(
            ProviderResponse(
                id=provider["id"],
                name=provider["name"],
                status=provider["status"],
                status_message=provider.get("status_message"),
                selected=provider["selected"],
                models=_serialize_models(provider["models"]),
                auth=ProviderAuthResponse(**provider["auth"]) if provider.get("auth") else None,
            )
        )
    return LLMOptionsResponse(
        active_provider=payload["active_provider"],
        active_model=payload["active_model"],
        providers=providers,
    )


@router.put("/llm-selection", response_model=SetModelResponse)
async def set_llm_selection(
    request: LLMSelectionRequest,
    settings_models_service: SettingsModelsService = Depends(get_settings_models_service_dep),
) -> SetModelResponse:
    payload = await settings_models_service.set_selection(
        provider_id=request.provider_id,
        model_id=request.model_id,
    )
    return SetModelResponse.model_validate(payload)


@router.get("/copilot/status", response_model=ProviderAuthResponse)
async def get_copilot_status(
    settings_models_service: SettingsModelsService = Depends(get_settings_models_service_dep),
) -> ProviderAuthResponse:
    payload = await settings_models_service.get_copilot_status()
    return ProviderAuthResponse(**payload)


@router.post("/copilot/login", response_model=CopilotActionResponse)
async def launch_copilot_login(
    settings_models_service: SettingsModelsService = Depends(get_settings_models_service_dep),
) -> CopilotActionResponse:
    payload = await settings_models_service.launch_copilot_login()
    return CopilotActionResponse(**payload)


@router.post("/copilot/logout", response_model=CopilotActionResponse)
async def logout_copilot(
    settings_models_service: SettingsModelsService = Depends(get_settings_models_service_dep),
) -> CopilotActionResponse:
    payload = await settings_models_service.logout_copilot()
    return CopilotActionResponse(**payload)


@router.get("/architect-profile", response_model=ArchitectProfileResponseContract)
async def get_architect_profile(
    db=Depends(get_db),
    architect_profile_service: ArchitectProfileService = Depends(get_architect_profile_service_dep),
) -> ArchitectProfileResponseContract:
    return await architect_profile_service.get_profile(db)


@router.put("/architect-profile", response_model=ArchitectProfileResponseContract)
async def update_architect_profile(
    request: ArchitectProfile,
    db=Depends(get_db),
    architect_profile_service: ArchitectProfileService = Depends(get_architect_profile_service_dep),
) -> ArchitectProfileResponseContract:
    return await architect_profile_service.update_profile(profile=request, db=db)


__all__ = [
    "_architect_profile_service",
    "_settings_models_service",
    "get_architect_profile_service_dep",
    "get_settings_models_service_dep",
    "router",
]
