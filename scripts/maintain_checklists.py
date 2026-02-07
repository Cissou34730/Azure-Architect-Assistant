#!/usr/bin/env python
"""Operational checklist maintenance commands."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select


def _ensure_backend_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    backend_path = repo_root / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))


_ensure_backend_on_path()

from app.agents_system.checklists.engine import ChecklistEngine  # noqa: E402
from app.agents_system.checklists.registry import ChecklistRegistry  # noqa: E402
from app.core.app_settings import get_settings  # noqa: E402
from app.models.checklist import Checklist, ChecklistItem, ChecklistItemEvaluation  # noqa: E402
from app.models.project import ProjectState  # noqa: E402
from app.projects_database import AsyncSessionLocal, close_database  # noqa: E402


def _build_engine() -> ChecklistEngine:
    settings = get_settings()
    registry = ChecklistRegistry(Path(settings.waf_template_cache_dir), settings)
    return ChecklistEngine(
        db_session_factory=AsyncSessionLocal,
        registry=registry,
        settings=settings,
    )


async def _cmd_stats(_: argparse.Namespace) -> int:
    async with AsyncSessionLocal() as session:
        checklist_count = (await session.execute(select(func.count(Checklist.id)))).scalar() or 0
        item_count = (await session.execute(select(func.count(ChecklistItem.id)))).scalar() or 0
        eval_count = (await session.execute(select(func.count(ChecklistItemEvaluation.id)))).scalar() or 0
    print(
        {
            "checklists": int(checklist_count),
            "items": int(item_count),
            "evaluations": int(eval_count),
        }
    )
    return 0


async def _cmd_sync_project(args: argparse.Namespace) -> int:
    engine = _build_engine()
    project_id = args.project_id
    if args.direction == "from-db":
        state = await engine.sync_db_to_project_state(project_id)
        print(state)
        return 0

    async with AsyncSessionLocal() as session:
        state_row = (
            await session.execute(select(ProjectState).where(ProjectState.project_id == project_id))
        ).scalar_one_or_none()
    if state_row is None:
        print({"status": "error", "reason": "project_state_not_found"})
        return 1

    try:
        payload = json.loads(state_row.state) if isinstance(state_row.state, str) else state_row.state
    except json.JSONDecodeError:
        print({"status": "error", "reason": "invalid_json_in_project_state"})
        return 1

    result = await engine.sync_project_state_to_db(project_id, payload)
    print(result)
    return 0 if result.get("status") != "error" else 1


async def _cmd_cleanup(args: argparse.Namespace) -> int:
    async with AsyncSessionLocal() as session:
        orphan_evals_result = await session.execute(
            select(ChecklistItemEvaluation.id)
            .outerjoin(ChecklistItem, ChecklistItem.id == ChecklistItemEvaluation.item_id)
            .where(ChecklistItem.id.is_(None))
        )
        orphan_eval_ids = [row[0] for row in orphan_evals_result.all()]

        orphan_items_result = await session.execute(
            select(ChecklistItem.id)
            .outerjoin(Checklist, Checklist.id == ChecklistItem.checklist_id)
            .where(Checklist.id.is_(None))
        )
        orphan_item_ids = [row[0] for row in orphan_items_result.all()]

        if not args.dry_run:
            if orphan_eval_ids:
                await session.execute(
                    delete(ChecklistItemEvaluation).where(ChecklistItemEvaluation.id.in_(orphan_eval_ids))
                )
            if orphan_item_ids:
                await session.execute(delete(ChecklistItem).where(ChecklistItem.id.in_(orphan_item_ids)))
            await session.commit()

    print(
        {
            "dry_run": args.dry_run,
            "orphan_evaluations": len(orphan_eval_ids),
            "orphan_items": len(orphan_item_ids),
        }
    )
    return 0


async def _cmd_refresh_templates(_: argparse.Namespace) -> int:
    settings = get_settings()
    registry = ChecklistRegistry(Path(settings.waf_template_cache_dir), settings)
    loaded = registry.refresh_from_cache()
    print({"templates_loaded": loaded})
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Checklist maintenance commands.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    stats = subparsers.add_parser("stats", help="Print checklist table stats.")
    stats.set_defaults(handler=_cmd_stats)

    sync_project = subparsers.add_parser("sync-project", help="Sync one project.")
    sync_project.add_argument("project_id", type=str)
    sync_project.add_argument("--direction", choices=["to-db", "from-db"], default="to-db")
    sync_project.set_defaults(handler=_cmd_sync_project)

    cleanup = subparsers.add_parser("cleanup", help="Delete orphan checklist rows.")
    cleanup.add_argument("--dry-run", action="store_true")
    cleanup.set_defaults(handler=_cmd_cleanup)

    refresh_templates = subparsers.add_parser("refresh-templates", help="Reload local template cache.")
    refresh_templates.set_defaults(handler=_cmd_refresh_templates)

    return parser


async def _main_async() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return await args.handler(args)


def main() -> int:
    try:
        return asyncio.run(_main_async())
    finally:
        asyncio.run(close_database())


if __name__ == "__main__":
    raise SystemExit(main())
