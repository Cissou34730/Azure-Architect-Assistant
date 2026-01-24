from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import httpx


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug agent chat + wafChecklist updates")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--message", required=True)
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
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=180.0) as client:
        lifespan_ctx = getattr(app.router, "lifespan_context", None)
        if lifespan_ctx is None:
            raise RuntimeError("FastAPI lifespan_context not available")

        async with lifespan_ctx(app):
            chat = await client.post(
                f"/api/agent/projects/{args.project_id}/chat",
                json={"message": args.message},
            )
            print("chat status", chat.status_code)
            data = chat.json()
            print("success", data.get("success"))
            print("error", data.get("error"))
            reasoning_steps = data.get("reasoning_steps") or data.get("reasoningSteps")
            if isinstance(reasoning_steps, list):
                print("reasoning steps", len(reasoning_steps))
                # Print last few steps to see tool results
                for step in reasoning_steps[-8:]:
                    if not isinstance(step, dict):
                        continue
                    name = step.get("tool") or step.get("tool_name") or step.get("name")
                    print("-", step.get("type"), name)
                    obs = step.get("observation")
                    if isinstance(obs, str) and ("aaa_record_validation_results" in obs or "AAA_STATE_UPDATE" in obs or "ERROR:" in obs):
                        print(obs[:1200])

            state = await client.get(f"/api/projects/{args.project_id}/state")
            state_data = state.json().get("projectState")
            waf = None
            if isinstance(state_data, dict):
                waf = state_data.get("wafChecklist") or state_data.get("waf_checklist")
            items = None
            if isinstance(waf, dict):
                items = waf.get("items")
            print("wafChecklist.items len", len(items) if isinstance(items, list) else None)


def main() -> None:
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
