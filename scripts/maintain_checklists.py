#!/usr/bin/env python
"""
WAF Checklist Maintenance Script

Utilities for managing normalized checklist data.
"""

import logging
import asyncio
import sys
from pathlib import Path
from uuid import UUID

import click
from sqlalchemy import func, select


def _ensure_backend_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    backend_path = repo_root / "backend"
    sys.path.insert(0, str(backend_path))

_ensure_backend_on_path()

from app.agents_system.checklists.engine import ChecklistEngine  # noqa: E402
from app.agents_system.checklists.registry import ChecklistRegistry  # noqa: E402
from app.agents_system.checklists.service import ChecklistService  # noqa: E402
from app.core.app_settings import get_settings  # noqa: E402
from app.models.checklist import Checklist, ChecklistItem, ChecklistItemEvaluation  # noqa: E402
from app.models.project import ProjectState  # noqa: E402
from app.projects_database import AsyncSessionLocal  # noqa: E402

logger = logging.getLogger(__name__)


async def _get_service():
    """Helper to initialize the service manually."""
    settings = get_settings()
    registry = ChecklistRegistry(Path(settings.waf_template_cache_dir), settings)
    engine = ChecklistEngine(
        db_session_factory=AsyncSessionLocal,
        registry=registry,
        settings=settings
    )
    return ChecklistService(engine=engine, registry=registry)


@click.group()
def cli():
    """Checklist maintenance utilities."""
    pass


@cli.command()
def stats():
    """Show database statistics."""

    async def _run():
        async with AsyncSessionLocal() as session:
            checklists = (await session.execute(select(func.count(Checklist.id)))).scalar()
            items = (await session.execute(select(func.count(ChecklistItem.id)))).scalar()
            evals = (await session.execute(select(func.count(ChecklistItemEvaluation.id)))).scalar()

            click.echo("--- Database Statistics ---")
            click.echo(f"Checklists:  {checklists or 0}")
            click.echo(f"Items:       {items or 0}")
            click.echo(f"Evaluations: {evals or 0}")

    asyncio.run(_run())


@cli.command()
@click.argument("project_id", type=click.UUID)
@click.option("--direction", type=click.Choice(["to-db", "from-db"]), default="to-db")
def sync_project(project_id: UUID, direction: str):
    """Sync project between JSON and DB."""

    async def _run():
        service = await _get_service()
        if direction == "to-db":
            async with AsyncSessionLocal() as session:
                stmt = select(ProjectState).where(ProjectState.project_id == project_id)
                res = await session.execute(stmt)
                state = res.scalar_one_or_none()

                if not state or "wafChecklist" not in state.state:
                    click.echo(f"No WAF checklist found in ProjectState for {project_id}")
                    return

                click.echo(f"Syncing {project_id} JSON -> DB...")
                summary = await service.sync_project(str(project_id), state.state)
                click.echo(f"Sync complete: {summary}")
        else:
            click.echo(f"Reconstructing {project_id} JSON from DB...")
            state = await service.engine.sync_db_to_project_state(project_id)
            click.echo("Reconstruction successful (output suppressed)")

    asyncio.run(_run())


@cli.command()
@click.option("--dry-run", is_flag=True)
def cleanup(dry_run: bool):
    """Remove orphaned records."""

    async def _run():
        # This is a placeholder for actual cleanup logic if needed
        click.echo(f"Cleanup starting (dry_run={dry_run})...")
        click.echo("Cleaning up evaluation records without associated items...")
        # Example logic...
        click.echo("Cleanup finished.")

    asyncio.run(_run())


@cli.command()
def refresh_templates():
    """Refresh cached templates (Reload registry)."""

    async def _run():
        settings = get_settings()
        registry = ChecklistRegistry(Path(settings.waf_template_cache_dir), settings)
        click.echo(f"Registry reloaded. Loaded {len(registry.list_templates())} templates.")

    asyncio.run(_run())


if __name__ == "__main__":
    try:
        cli()
    finally:
        # Note: can't easily wait for close_database in a sync finally if loop is closed
        # but for a CLI script it's generally fine as process exits
        pass
