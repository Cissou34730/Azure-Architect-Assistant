from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import httpx


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug /api/query/chat in-process")
    parser.add_argument(
        "--kb-root",
        type=str,
        default=None,
        help="Override KNOWLEDGE_BASES_ROOT before app import (path containing <kb>/index)",
    )
    parser.add_argument(
        "--question",
        type=str,
        default="What are the Azure Well-Architected Framework pillars?",
    )
    parser.add_argument("--top-k-per-kb", type=int, default=1)
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
            response = await client.post(
                "/api/query/chat",
                json={
                    "question": args.question,
                    "top_k_per_kb": args.top_k_per_kb,
                },
            )
            print("status", response.status_code)
            print(response.json())


def main() -> None:
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
