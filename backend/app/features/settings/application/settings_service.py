"""Service layer for provider-aware LLM runtime settings."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException

from app.shared.ai.ai_service import AIServiceManager
from app.shared.ai.config import AIConfig
from app.shared.ai.models_service import ModelsService
from app.shared.ai.providers.copilot_runtime import get_copilot_runtime
from app.shared.config.app_settings import get_app_settings
from app.shared.runtime.runtime_ai_selection import persist_runtime_ai_selection

_SAFE_PROVIDER_PROBE_ERRORS = (
    AttributeError,
    NotImplementedError,
    RuntimeError,
    TimeoutError,
    ValueError,
)


class SettingsModelsService:
    """Coordinates provider-aware model listing and runtime switching."""

    def _get_fallback_provider_and_model(self) -> tuple[str, str]:
        settings = get_app_settings()
        provider = settings.effective_ai_llm_provider
        if provider == "azure":
            return provider, settings.effective_azure_llm_deployment
        if provider == "copilot":
            return provider, settings.effective_copilot_default_model
        return provider, settings.effective_openai_llm_model

    async def get_available_models(
        self, *, refresh: bool
    ) -> tuple[list[dict[str, Any]], datetime]:
        models, cached_at = await self._get_active_provider_models(refresh=refresh)
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
        try:
            ai_service = AIServiceManager.get_instance()
            return ai_service.get_llm_model()
        except Exception:  # noqa: BLE001
            _, model = self._get_fallback_provider_and_model()
            return model

    def get_current_provider(self) -> str:
        try:
            ai_service = AIServiceManager.get_instance()
            return ai_service.get_llm_provider_name()
        except Exception:  # noqa: BLE001
            provider, _ = self._get_fallback_provider_and_model()
            return provider

    async def get_llm_options(self, *, refresh: bool) -> dict[str, Any]:
        active_provider = self.get_current_provider()
        active_model = self.get_current_model()
        providers = await self._build_provider_payloads(active_provider=active_provider, refresh=refresh)
        return {
            "active_provider": active_provider,
            "active_model": active_model,
            "providers": providers,
        }

    async def get_copilot_status(self) -> dict[str, Any]:
        runtime = await get_copilot_runtime(AIConfig.default())
        status = await runtime.get_status()
        payload = {
            "available": status.available,
            "authenticated": status.authenticated,
            "state": status.state,
            "login": status.login,
            "auth_type": status.auth_type,
            "host": status.host,
            "status_message": status.status_message,
            "cli_path": status.cli_path,
        }
        if status.available and status.authenticated:
            try:
                quota = await runtime.get_quota()
            except _SAFE_PROVIDER_PROBE_ERRORS:
                quota = None
            payload["quota"] = quota
        else:
            payload["quota"] = None
        return payload

    async def launch_copilot_login(self) -> dict[str, Any]:
        runtime = await get_copilot_runtime(AIConfig.default())
        return await runtime.launch_login()

    async def logout_copilot(self) -> dict[str, Any]:
        runtime = await get_copilot_runtime(AIConfig.default())
        return await runtime.logout()

    async def set_model(self, *, model_id: str) -> dict[str, Any]:
        current_provider = self.get_current_provider()
        return await self.set_selection(provider_id=current_provider, model_id=model_id)

    async def set_selection(self, *, provider_id: str, model_id: str) -> dict[str, Any]:
        probe_config = self._build_probe_config(
            provider_id=provider_id,
            model_id=model_id,
            base_config=AIConfig.default(),
        )

        probe_service = AIServiceManager.create_probe(probe_config)

        if provider_id == "copilot":
            probe_config_check = self._build_probe_config(
                provider_id=provider_id,
                model_id=model_id,
                base_config=AIConfig.default(),
            )
            if not probe_config_check.copilot_token:
                raise HTTPException(
                    status_code=400,
                    detail="Copilot token is not configured. Set AI_COPILOT_TOKEN or GITHUB_TOKEN.",
                )
            runtime_model_ids = await self._safe_provider_model_ids(probe_service)
            fallback_model_ids = self._copilot_fallback_model_ids(probe_config)
            candidate_ids = runtime_model_ids or fallback_model_ids
            if candidate_ids and model_id not in candidate_ids:
                visible = ", ".join(sorted(candidate_ids))
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Model '{model_id}' is not available for provider '{provider_id}'. "
                        f"Available: {visible}"
                    ),
                )
        else:
            runtime_model_ids = await self._safe_provider_model_ids(probe_service)
            if runtime_model_ids and model_id not in runtime_model_ids:
                visible = ", ".join(sorted(runtime_model_ids))
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Model '{model_id}' is not available for provider '{provider_id}'. "
                        f"Available: {visible}"
                    ),
                )

        await AIServiceManager.reinitialize_with_selection(provider_id, model_id)
        self._persist_runtime_selection(provider_id=provider_id, model_id=model_id)
        current_model = self.get_current_model()
        current_provider = self.get_current_provider()
        return {
            "success": current_model == model_id and current_provider == provider_id,
            "current_model": current_model,
            "current_provider": current_provider,
            "message": (
                f"Provider changed to {provider_id} / {model_id}"
                if current_model == model_id and current_provider == provider_id
                else "Provider/model change verification failed"
            ),
        }

    async def _get_active_provider_models(
        self, *, refresh: bool
    ) -> tuple[list[Any], datetime]:
        models_service = ModelsService()
        return await models_service.get_available_models(force_refresh=refresh)

    async def _build_provider_payloads(
        self,
        *,
        active_provider: str,
        refresh: bool,
    ) -> list[dict[str, Any]]:
        base_config = AIConfig.default()
        providers: list[str] = ["openai", "azure", "copilot"]
        payloads: list[dict[str, Any]] = []

        for provider_id in providers:
            try:
                models_payload, status, status_message = await self._get_provider_listing(
                    provider_id=provider_id,
                    base_config=base_config,
                    refresh=refresh,
                    active_provider=active_provider,
                )
            except Exception as exc:  # noqa: BLE001
                models_payload = []
                status = "error"
                status_message = str(exc)

            provider_payload = {
                "id": provider_id,
                "name": self._provider_name(provider_id),
                "status": status,
                "status_message": status_message,
                "selected": provider_id == active_provider,
                "models": models_payload,
            }
            if provider_id == "copilot":
                provider_payload["auth"] = (
                    await self.get_copilot_status() if provider_id == active_provider else None
                )
            payloads.append(provider_payload)

        return payloads

    async def _get_provider_listing(
        self,
        *,
        provider_id: str,
        base_config: AIConfig,
        refresh: bool,
        active_provider: str,
    ) -> tuple[list[dict[str, Any]], str, str | None]:
        model_id = self._default_model_for_provider(base_config, provider_id)
        provider_config = self._build_probe_config(
            provider_id=provider_id,
            model_id=model_id,
            base_config=base_config,
        )
        models_service = ModelsService(config=provider_config)
        models, _ = await models_service.get_available_models(
            force_refresh=refresh,
            cache_only=provider_id != active_provider and not refresh,
        )
        return (
            [
                {
                    "id": m.id,
                    "name": m.name,
                    "context_window": m.context_window,
                    "pricing": m.pricing,
                }
                for m in models
            ],
            "ready",
            None,
        )

    @staticmethod
    def _provider_name(provider_id: str) -> str:
        names = {
            "openai": "OpenAI",
            "azure": "Azure OpenAI",
            "copilot": "GitHub Copilot",
        }
        return names.get(provider_id, provider_id)

    @staticmethod
    def _default_model_for_provider(base_config: AIConfig, provider_id: str) -> str:
        if provider_id == "azure":
            return base_config.azure_llm_deployment
        if provider_id == "copilot":
            return base_config.copilot_default_model
        return base_config.openai_llm_model

    @staticmethod
    def _build_probe_config(
        *,
        provider_id: str,
        model_id: str,
        base_config: AIConfig,
    ) -> AIConfig:
        return AIServiceManager._build_config_for_selection(
            provider_id,
            model_id,
            base_config=base_config.model_copy(
                update={
                    "fallback_enabled": False,
                    "fallback_provider": "none",
                }
            ),
        )

    @staticmethod
    def _default_probe_timeout() -> float:
        return 20.0

    @staticmethod
    async def _safe_provider_model_ids(probe_service: Any) -> set[str]:
        try:
            runtime_models = await probe_service.list_llm_runtime_models()
        except _SAFE_PROVIDER_PROBE_ERRORS:
            return set()

        ids: set[str] = set()
        for item in runtime_models:
            if not isinstance(item, dict):
                continue
            value = item.get("id") or item.get("model")
            if isinstance(value, str) and value:
                ids.add(value)
        return ids

    @staticmethod
    def _copilot_fallback_model_ids(config: AIConfig) -> set[str]:
        ids = {
            item.strip()
            for item in config.copilot_allowed_models.split(",")
            if item.strip()
        }
        if config.copilot_default_model:
            ids.add(config.copilot_default_model)
        return ids

    @staticmethod
    def _persist_runtime_selection(*, provider_id: str, model_id: str) -> None:
        settings = get_app_settings()
        runtime_ai_selection_path = getattr(settings, "runtime_ai_selection_path", None)
        if runtime_ai_selection_path is None:
            return
        persist_runtime_ai_selection(
            runtime_ai_selection_path,
            llm_provider=provider_id,
            model_id=model_id,
        )
        cache_clear = getattr(get_app_settings, "cache_clear", None)
        if callable(cache_clear):
            cache_clear()


__all__ = ["SettingsModelsService"]
