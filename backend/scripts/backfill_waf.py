"""
Backfill script to migrate WAF checklists from legacy ProjectState JSON to normalized SQL tables.

Usage: 
  uv run backend/scripts/backfill_waf.py [--dry-run] [--project-id <id>]
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

from app.agents_system.checklists.engine import ChecklistEngine
from app.agents_system.checklists.registry import ChecklistRegistry
from app.core.app_settings import get_settings
from app.models.project import Project, ProjectState
from app.projects_database import AsyncSessionLocal
from app.services.backfill_service import BackfillService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def backfill_project(project, session, engine, dry_run=False):
    """Backfill a single project's WAF data."""
    logger.info(f"Processing project {project.id} ({project.name})")

    # Get legacy state
    stmt = select(ProjectState).where(ProjectState.project_id == project.id)
    result = await session.execute(stmt)
    state_obj = result.scalar_one_or_none()

    if not state_obj or not state_obj.state:
        logger.warning(f"  No state found for project {project.id}")
        return 0

    evals = extract_waf_evaluations(state_obj.state)
    if not evals:
        logger.info(f"  No legacy WAF data found in project {project.id}")
        return 0

    logger.info(f"  Found {len(evals)} evaluations to migrate.")

    if dry_run:
        logger.info(f"  [DRY RUN] Would migrate {len(evals)} items.")
        return len(evals)

    # Ensure checklist instantiated
    template_slug = state_obj.state.get("wafChecklist", {}).get("slug", "waf-2024")
    checklist = await engine.instantiate_checklist(project.id, template_slug)
    if not checklist:
        logger.error(f"  Failed to instantiate checklist {template_slug} for project {project.id}")
        return 0

    for eval_data in evals:
        await engine.update_item_evaluation(
            item_id=eval_data["item_id"],
            project_id=project.id,
            status=eval_data["status"],
            evidence=eval_data["evidence"],
            evaluator="legacy-migration"
        )

    await engine.calculate_progress(checklist.id)
    logger.info(f"  Successfully migrated project {project.id}. Progress: {checklist.completion_percentage}%")
    return len(evals)

async def main():
    parser = argparse.ArgumentParser(description="Backfill WAF checklists.")
    parser.add_argument("--dry-run", action="store_true", help="Don't commit changes")
    parser.add_argument("--project-id", help="Only backfill a specific project")
    parser.add_argument("--verify", action="store_true", help="Verify consistency after backfill or for random sample")
    args = parser.parse_args()

    settings = get_settings()
    session_factory = AsyncSessionLocal

    registry = ChecklistRegistry(Path(settings.waf_template_cache_dir), settings)
    engine = ChecklistEngine(
        db_session_factory=session_factory,
        registry=registry,
        settings=settings
    )
    service = BackfillService(engine, session_factory)

    if args.project_id:
        logger.info(f"Backfilling project {args.project_id}")
        res = await service.backfill_project(args.project_id, dry_run=args.dry_run)
        logger.info(f"Result: {res}")
        
        if args.verify and res.get("status") == "success":
            logger.info(f"Verifying project {args.project_id}")
            is_consistent, diffs = await service.verify_project_consistency(args.project_id)
            if is_consistent:
                logger.info("  Verification PASSED")
            else:
                logger.error(f"  Verification FAILED: {diffs}")
    else:
        logger.info("Backfilling all projects")
        summary = await service.backfill_all_projects(
            dry_run=args.dry_run, 
            verify_sample=args.verify
        )
        logger.info(f"Summary: {summary}")

if __name__ == "__main__":
    asyncio.run(main())
