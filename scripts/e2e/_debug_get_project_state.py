from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import httpx


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug GET /api/projects/{id}/state in-process")
    parser.add_argument("--project-id", required=True)
    parser.add_argument(
        "--kb-root",
        type=str,
        default=None,
        help="Override KNOWLEDGE_BASES_ROOT before app import",
    )
    return parser.parse_args()


async def _main_async() -> None:
    args = _parse_args()

    if args.kb_root:
        os.environ["KNOWLEDGE_BASES_ROOT"] = args.kb_root

    repo_root = Path(__file__).resolve().parents[2]
    backend_root = repo_root / "backend"
    sys.path.insert(0, str(backend_root))

    from app.core.app_settings import get_app_settings

    get_app_settings.cache_clear()

    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        lifespan_ctx = getattr(app.router, "lifespan_context", None)
        if lifespan_ctx is None:
            raise RuntimeError("FastAPI lifespan_context not available")

        async with lifespan_ctx(app):
            resp = await client.get(f"/api/projects/{args.project_id}/state")
            print("status", resp.status_code)
            data = resp.json()
            project_state = data.get("projectState")
            if not isinstance(project_state, dict):
                print("projectState not found or not a dict")
                print(data)
                return

            waf = project_state.get("wafChecklist") or project_state.get("waf_checklist")
            print("wafChecklist type:", type(waf).__name__)
            print("wafChecklist keys:", list(waf.keys()) if isinstance(waf, dict) else None)
            items = None
            if isinstance(waf, dict):
                items = waf.get("items")
            print("items type:", type(items).__name__)
            if isinstance(items, list):
                print("items len:", len(items))
                if items:
                    print("first item keys:", list(items[0].keys()))
            else:
                print("items:", items)


def main() -> None:
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
