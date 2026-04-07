"""Runtime guardrails that enforce API architecture conventions."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI


def _api_roots() -> tuple[Path, ...]:
    features_root = Path(__file__).resolve().parents[2] / "features"
    return tuple(
        sorted(path for path in features_root.glob("*/api") if path.is_dir())
    )


def enforce_router_guardrails(app: FastAPI) -> None:
    """Validate API boundaries and route conventions at startup."""
    api_roots = _api_roots()

    operations_modules: list[str] = []
    direct_registry_imports: list[str] = []
    for api_root in api_roots:
        for module_path in sorted(api_root.rglob("*.py")):
            content = module_path.read_text(encoding="utf-8")
            relative_path = str(module_path.relative_to(api_root.parents[2]))
            if module_path.name.endswith("_operations.py"):
                operations_modules.append(relative_path)
            is_router_entrypoint = module_path.name.endswith("router.py")
            if is_router_entrypoint and "app.service_registry" in content:
                direct_registry_imports.append(relative_path)

    if operations_modules:
        details = ", ".join(operations_modules)
        raise RuntimeError(
            f"Router guardrail violation: router-local operations modules are forbidden ({details})"
        )

    if direct_registry_imports:
        details = ", ".join(direct_registry_imports)
        raise RuntimeError(
            f"Router guardrail violation: direct app.service_registry imports in routers ({details})"
        )

    api_v1_paths = [
        route.path for route in app.routes if getattr(route, "path", "").startswith("/api/v1")
    ]
    if api_v1_paths:
        details = ", ".join(sorted(api_v1_paths))
        raise RuntimeError(
            f"Router guardrail violation: /api/v1 routes are not allowed ({details})"
        )
