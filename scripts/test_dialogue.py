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
from app.agents_system.runner import get_agent_runner
from app.lifecycle import startup as app_startup, shutdown as app_shutdown
from app.projects_database import AsyncSessionLocal
from sqlalchemy import select
from app.models.project import Project
import json
import uuid


async def run_dialogue(project_id: str, messages: list[str]) -> None:
    settings = get_settings()

    # Ensure project exists
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(Project).where(Project.id == project_id))
        proj = existing.scalars().first()
        if not proj:
            proj = Project(id=project_id, name=project_id, text_requirements="Test project")
            db.add(proj)
            await db.commit()
            await db.refresh(proj)
            print(f"Created project {project_id}")

    # Start application lifecycle so agent runner and services are initialized
    await app_startup()

    # Use LangGraph project-aware adapter for multi-turn conversation
    # (LangGraph-native path will be used; errors may fall back internally)
    runner = await get_agent_runner()

    conversation_history = []

    from app.agents_system.langgraph.adapter import execute_project_chat

    for i, msg in enumerate(messages):
        print(f"\n--- Turn {i+1} user -> agent:\n{msg}\n")
        async with AsyncSessionLocal() as db:
            result = await execute_project_chat(project_id, msg, db)
            print("Agent success:", result.get("success"))
            print("Agent output:\n", result.get("answer"))

    # Shutdown lifecycle to cleanly close services
    try:
        await app_shutdown()
    except Exception as e:
        print(f"Warning: lifecycle shutdown failed: {e}")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Simulate a multi-turn dialogue with the agent (script-only)")
    p.add_argument("project_id", help="Project id to scope the chat")
    p.add_argument("messages", nargs="+", help="Messages to send in order")
    args = p.parse_args()

    asyncio.run(run_dialogue(args.project_id, args.messages))
