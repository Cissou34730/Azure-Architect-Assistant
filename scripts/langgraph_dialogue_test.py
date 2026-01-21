from __future__ import annotations

import asyncio
import sys
from pathlib import Path
import json
from sqlalchemy import select


def _ensure_backend_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    backend_path = repo_root / "backend"
    sys.path.insert(0, str(backend_path))


_ensure_backend_on_path()


async def run_test(project_id: str, message: str) -> None:
    # Import application runtime helpers lazily so we can fail fast and
    # diagnose where imports or startup hang.
    print("[debug] Importing app lifecycle and DB helpers...")
    try:
        from app.lifecycle import startup as app_startup, shutdown as app_shutdown
        from app.projects_database import AsyncSessionLocal
        from app.models.project import Project, ConversationMessage
    except Exception as e:
        print("[error] Failed importing backend application modules:", repr(e))
        raise

    # Start services with a timeout so we can detect slow startup issues early.
    print("[debug] Starting application lifecycle (timeout=60s)...")
    try:
        await asyncio.wait_for(app_startup(), timeout=60)
    except asyncio.TimeoutError:
        print("[error] app_startup() timed out after 60s")
        raise
    except Exception as e:
        print("[error] app_startup() raised:", repr(e))
        raise

    # ensure project exists
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(Project).where(Project.id == project_id))
        proj = existing.scalars().first()
        if not proj:
            proj = Project(id=project_id, name=project_id, text_requirements=message)
            db.add(proj)
            await db.commit()
            await db.refresh(proj)
            print(f"Created project {project_id}")

    # Run LangGraph project-aware chat
    from app.agents_system.langgraph.adapter import execute_project_chat

    async with AsyncSessionLocal() as db:
        result = await execute_project_chat(project_id, message, db)
        print("Agent returned success:", result.get("success"))
        print("Answer:\n", result.get("answer"))
        try:
            await db.commit()
            print("[debug] Committed DB session after graph execution")
        except Exception as e:
            print("[warn] Failed to commit DB session:", repr(e))

    # Verify messages persisted in DB
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(ConversationMessage).where(ConversationMessage.project_id == project_id).order_by(ConversationMessage.timestamp))
        msgs = res.scalars().all()
        print(f"Found {len(msgs)} messages for project {project_id}")
        for m in msgs:
            print(f"- {m.role}: {m.content[:200]}...")

    # Shutdown services
    print("[debug] Shutting down application lifecycle...")
    try:
        await asyncio.wait_for(app_shutdown(), timeout=30)
    except Exception as e:
        print("[warn] app_shutdown() raised/failed:", repr(e))


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Run LangGraph native dialogue and verify DB persistence")
    p.add_argument("project_id", help="Project id to use")
    p.add_argument("message", help="Message to send to agent")
    args = p.parse_args()

    asyncio.run(run_test(args.project_id, args.message))

