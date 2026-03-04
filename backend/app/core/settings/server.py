"""Server / application identity settings mixin."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ServerSettingsMixin(BaseModel):
    env: str = Field("development")
    app_version: str = "4.0.0"
    backend_host: str = Field("0.0.0.0")
    backend_port: int = Field(8000, ge=1, le=65535)
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])
    log_level: str = Field("INFO")

    # Optional env-file keys silenced to avoid extras-forbid rejection
    frontend_port: int | None = None
    backend_url: str | None = None
    vite_banner_message: str | None = None
    vite_api_base: str | None = None

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value  # type: ignore[return-value]
