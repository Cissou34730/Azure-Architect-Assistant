from __future__ import annotations

import asyncio
import sys
from pathlib import Path


def _ensure_backend_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    backend_path = repo_root / "backend"
    sys.path.insert(0, str(backend_path))


_ensure_backend_on_path()

from app.core.config import get_settings
from app.agents_system.runner import initialize_agent_runner, shutdown_agent_runner, get_agent_runner
from app.services.mcp.learn_mcp_client import MicrosoftLearnMCPClient
from app.projects_database import AsyncSessionLocal
from app.lifecycle import startup as app_startup, shutdown as app_shutdown
from sqlalchemy import select
import json
from app.models.project import Project
from pathlib import Path


async def main(project_id: str, message: str, project_json: str | None = None) -> None:
    settings = get_settings()

    # Run application lifecycle startup to initialize KBs, DB, and other services
    try:
        await app_startup()
    except Exception as e:
        print(f"Application lifecycle startup failed: {e}")
        return

    # Acquire a DB session, ensure project exists (optionally from JSON), then call the LangGraph adapter
    async with AsyncSessionLocal() as db:
        # Optionally create project from JSON if provided
        if project_json:
            try:
                p = Path(project_json)
                data = json.loads(p.read_text(encoding="utf-8"))
                # If JSON provides an explicit id, ensure it matches requested project_id
                json_id = data.get("id")
                if json_id and str(json_id) != str(project_id):
                    raise ValueError(f"JSON id '{json_id}' does not match project_id '{project_id}'")

                # Check if project already exists
                existing = await db.execute(select(Project).where(Project.id == project_id))
                proj = existing.scalars().first()
                if not proj:
                    proj = Project(
                        id=str(project_id),
                        name=data.get("name") or str(project_id),
                        text_requirements=(data.get("specification") or {}).get("text") or data.get("specification") or "",
                    )
                    db.add(proj)
                    await db.commit()
                    await db.refresh(proj)
                    print(f"Project '{project_id}' created from JSON")
                else:
                    print(f"Project '{project_id}' already exists in DB")
            except Exception as e:
                print(f"Failed to create project from JSON: {e}")

        try:
            # Import adapter lazily (matches router behavior)
            from app.agents_system.langgraph.adapter import execute_project_chat

            result = await execute_project_chat(project_id, message, db)
            print("Success:", result.get("success"))
            print("Answer:\n", result.get("answer") or "")
        except Exception as e:
            import traceback, json as _json

            print("Project chat execution failed:", type(e).__name__, str(e))
            traceback.print_exc()

            # Dump known SDK/HTTP error attributes if present
            for attr in ("http_status", "status_code", "response", "http_body", "json_body", "body"):
                if hasattr(e, attr):
                    try:
                        val = getattr(e, attr)
                        print(f"{attr}:", _json.dumps(val, indent=2) if isinstance(val, (dict, list)) else val)
                    except Exception:
                        print(f"{attr}: (unprintable)")

            # Some SDKs attach .args[0] with response text
            try:
                if e.args:
                    print("Exception args:", e.args)
            except Exception:
                pass

            print("Detected error during agent call. You can inspect the printed payload above to determine whether this is a 400 from OpenAI or another upstream service.\n")

    # Run application lifecycle shutdown to cleanly stop services
    try:
        await app_shutdown()
    except Exception as e:
        print(f"Application lifecycle shutdown failed: {e}")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Call project-aware agent chat without HTTP")
    p.add_argument("project_id", help="Project id to scope the chat")
    p.add_argument("message", help="Message to send to the agent")
    p.add_argument("project_json", nargs="?", help="Optional path to project JSON to create the project if missing")
    args = p.parse_args()

    asyncio.run(main(args.project_id, args.message, args.project_json))
