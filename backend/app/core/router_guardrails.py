"""Runtime guardrails that enforce router architecture conventions."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI


def _routers_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "routers"


def enforce_router_guardrails(app: FastAPI) -> None:
    """Validate router boundaries and route conventions at startup."""
    router_dir = _routers_dir()

    operations_modules = sorted(router_dir.rglob("*_operations.py"))
    if operations_modules:
        details = ", ".join(str(path.relative_to(router_dir.parent)) for path in operations_modules)
        raise RuntimeError(
            f"Router guardrail violation: router-local operations modules are forbidden ({details})"
        )

    direct_registry_imports: list[str] = []
    for router_file in sorted(router_dir.rglob("*.py")):
        content = router_file.read_text(encoding="utf-8")
        if "app.service_registry" in content:
            direct_registry_imports.append(str(router_file.relative_to(router_dir.parent)))
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
