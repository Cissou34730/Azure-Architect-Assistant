#!/usr/bin/env python
"""CLI for WAF checklist backfill and verification tasks."""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
from pathlib import Path
from typing import Any


def _ensure_backend_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    backend_path = repo_root / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))


_ensure_backend_on_path()

from app.agents_system.checklists.engine import ChecklistEngine  # noqa: E402
from app.agents_system.checklists.registry import ChecklistRegistry  # noqa: E402
from app.core.app_settings import get_settings  # noqa: E402
from app.models.project import ProjectState  # noqa: E402
from app.projects_database import AsyncSessionLocal, close_database  # noqa: E402
from app.services.backfill_service import BackfillService  # noqa: E402


def _build_services(batch_size: int) -> tuple[ChecklistEngine, BackfillService]:
    settings = get_settings()
    registry = ChecklistRegistry(Path(settings.waf_template_cache_dir), settings)
    engine = ChecklistEngine(
        db_session_factory=AsyncSessionLocal,
        registry=registry,
        settings=settings,
    )
    backfill = BackfillService(
        engine=engine,
        db_session_factory=AsyncSessionLocal,
        batch_size=batch_size,
    )
    return engine, backfill


async def _cmd_backfill(args: argparse.Namespace) -> int:
    _, service = _build_services(args.batch_size)
    summary = await service.backfill_all_projects(
        dry_run=args.dry_run,
        verify_sample=args.verify,
    )
    print(summary)
    return 0


async def _cmd_backfill_project(args: argparse.Namespace) -> int:
    _, service = _build_services(args.batch_size)
    result = await service.backfill_project(args.project_id, dry_run=args.dry_run)
    print(result)
    if args.verify and result.get("status") == "success":
        ok, diffs = await service.verify_project_consistency(args.project_id)
        print({"verified": ok, "diffs": diffs})
    return 0 if result.get("status") != "error" else 1


async def _cmd_progress(args: argparse.Namespace) -> int:
    _, service = _build_services(args.batch_size)
    progress = await service.get_backfill_progress()
    print(progress)
    return 0


async def _cmd_verify(args: argparse.Namespace) -> int:
    _, service = _build_services(args.batch_size)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            ProjectState.__table__.select().where(ProjectState.state.like('%"wafChecklist"%'))
        )
        rows = result.fetchall()
    project_ids = [str(row.project_id) for row in rows]
    if not project_ids:
        print({"verified_projects": 0, "failures": []})
        return 0

    sample_size = min(args.sample_size, len(project_ids))
    sampled = random.sample(project_ids, sample_size)  # noqa: S311
    failures: list[dict[str, Any]] = []
    for project_id in sampled:
        ok, diffs = await service.verify_project_consistency(project_id)
        if not ok:
            failures.append({"project_id": project_id, "diffs": diffs})

    print(
        {
            "verified_projects": sample_size,
            "failed_projects": len(failures),
            "failures": failures,
        }
    )
    return 0 if not failures else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WAF normalized checklist backfill tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backfill = subparsers.add_parser("backfill", help="Backfill all projects.")
    backfill.add_argument("--dry-run", action="store_true")
    backfill.add_argument("--verify", action="store_true")
    backfill.add_argument("--batch-size", type=int, default=50)
    backfill.set_defaults(handler=_cmd_backfill)

    backfill_project = subparsers.add_parser("backfill-project", help="Backfill one project.")
    backfill_project.add_argument("project_id", type=str)
    backfill_project.add_argument("--dry-run", action="store_true")
    backfill_project.add_argument("--verify", action="store_true")
    backfill_project.add_argument("--batch-size", type=int, default=50)
    backfill_project.set_defaults(handler=_cmd_backfill_project)

    progress = subparsers.add_parser("progress", help="Show migration progress.")
    progress.add_argument("--batch-size", type=int, default=50)
    progress.set_defaults(handler=_cmd_progress)

    verify = subparsers.add_parser("verify", help="Verify consistency sample.")
    verify.add_argument("--sample-size", type=int, default=10)
    verify.add_argument("--batch-size", type=int, default=50)
    verify.set_defaults(handler=_cmd_verify)

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
