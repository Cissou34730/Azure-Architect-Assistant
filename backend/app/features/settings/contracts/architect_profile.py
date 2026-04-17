"""Architect profile API contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.features.settings.domain.architect_profile import ArchitectProfile


class ArchitectProfileResponseContract(BaseModel):
    """Architect profile payload returned by the settings API."""

    model_config = ConfigDict(populate_by_name=True)

    profile: ArchitectProfile
    updated_at: str | None = Field(default=None, alias="updatedAt")

