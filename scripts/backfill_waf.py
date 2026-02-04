#!/usr/bin/env python
"""
WAF Checklist Backfill Script

Migrates existing ProjectState.state['wafChecklist'] JSON
to normalized database tables.

Usage:
    python scripts/backfill_waf.py --dry-run --batch-size 50
    python scripts/backfill_waf.py --execute --verify
    python scripts/backfill_waf.py --project-id <uuid>
"""

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID


def _ensure_backend_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    backend_path = repo_root / "backend"
    sys.path.insert(0, str(backend_path))

_ensure_backend_on_path()

from app.agents_system.checklists.engine import ChecklistEngine  # noqa: E402
from app.projects_database import AsyncSessionLocal, close_database  # noqa: E402
from app.services.backfill_service import BackfillService  # noqa: E402


async def _run_single_project(service: BackfillService, project_id: str, dry_run: bool, verify: bool):
    """Backfill a single project."""
    pid = UUID(project_id)
    print(f"Backfilling project {pid}...")
    result = await service.backfill_project(pid, dry_run=dry_run)
    print(f"Result: {result}")

    if verify:
        print("Verifying consistency...")
        consistent, diffs = await service.verify_project_consistency(pid)
        print("Consistency check PASSED" if consistent else f"Consistency check FAILED: {diffs}")


async def _run_all_projects(service: BackfillService, dry_run: bool, verify: bool):
    """Backfill all projects."""
    print(f"Starting backfill for all projects (dry_run={dry_run}, verify={verify})...")
    summary = await service.backfill_all_projects(
        dry_run=dry_run,
        verify_sample=verify
    )

    print("\nBackfill Summary:")
    print(f"Total projects found: {summary['total_projects']}")
    print(f"Processed: {summary['processed']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Errors: {len(summary['errors'])}")

    if verify:
        print(f"Verification Sample Passed: {summary['verification_passed']}")
        for err in summary['verification_errors'][:5]:
            print(f"  Project {err['project_id']}: {err['diffs']}")

    if summary['errors']:
        print("\nLast 5 Errors:")
        for err in summary['errors'][-5:]:
            print(f"  Project {err['project_id']}: {err['error']}")


async def main():
    parser = argparse.ArgumentParser(description="Backfill WAF checklists to normalized DB.")
    parser.add_argument("--dry-run", action="store_true", help="Validate but don't write to DB")
    parser.add_argument("--execute", action="store_true", help="Actually write to DB")
    parser.add_argument("--verify", action="store_true", help="Run verification checks on random sample")
    parser.add_argument("--batch-size", type=int, default=50, help="Number of projects to process in a batch")
    parser.add_argument("--project-id", type=str, help="Backfill a specific project only")

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("Please specify either --dry-run or --execute")
        return

    # Initialize Engine and Service
    engine = ChecklistEngine(db_session_factory=AsyncSessionLocal)
    service = BackfillService(
        engine=engine,
        db_session_factory=AsyncSessionLocal,
        batch_size=args.batch_size
    )

    try:
        if args.project_id:
            await _run_single_project(service, args.project_id, args.dry_run, args.verify)
        else:
            await _run_all_projects(service, args.dry_run, args.verify)
    finally:
        await close_database()

if __name__ == "__main__":
    asyncio.run(main())
