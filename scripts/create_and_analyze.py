"""
Create a project from a JSON file and run document analysis, all without HTTP.

Usage:
  PYTHONPATH=backend python scripts/create_and_analyze.py path/to/project.json <project-id>

Behavior:
- If the project id does not exist, it is created using the Project model.
- Then `DocumentService.analyze_documents` is invoked to populate ProjectState.
- On successful creation + analysis the script prints exactly: project created
- If the project already exists, the script prints: project exists
"""
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


async def _create_and_analyze(json_path: str, project_id: str) -> str:
    # Lazy imports to keep module import lightweight
    from app.projects_database import AsyncSessionLocal
    from app.models.project import Project
    from app.models import ProjectState
    from app.routers.project_management.services.document_service import DocumentService
    from sqlalchemy import select

    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    # Require explicit id in JSON and validate it matches the provided project_id
    json_id = data.get("id")
    if not json_id:
        raise ValueError("Project JSON must include an 'id' field that matches the provided project id")
    if str(json_id) != str(project_id):
        raise ValueError(f"Project JSON id '{json_id}' does not match provided project id '{project_id}'")

    name = data.get("name")
    if not name or not str(name).strip():
        raise ValueError("Project JSON must include a non-empty 'name' field")

    spec = data.get("specification") or {}
    spec_text = None
    if isinstance(spec, dict):
        spec_text = spec.get("text")
    if not spec_text:
        spec_text = data.get("description") or data.get("textRequirements")

    async with AsyncSessionLocal() as db:
        # Check if project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        existing = result.scalar_one_or_none()
        created = False
        if not existing:
            # create
            created_at = datetime.now(timezone.utc).isoformat()
            project = Project(id=str(project_id), name=str(name).strip(), created_at=created_at)
            if spec_text:
                project.text_requirements = str(spec_text)
            db.add(project)
            await db.commit()
            await db.refresh(project)
            created = True

        # Run analysis (this will raise if no documents/text present)
        service = DocumentService()
        state = await service.analyze_documents(project_id, db)

        # verify ProjectState exists
        res = await db.execute(select(ProjectState).where(ProjectState.project_id == project_id))
        state_rec = res.scalar_one_or_none()
        if not state_rec:
            raise RuntimeError("Analysis completed but ProjectState not persisted")

        return "project created" if created else "project exists"


def main(argv: Optional[list] = None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) < 2:
        print("Usage: python scripts/create_and_analyze.py path/to/project.json <project-id>")
        sys.exit(2)
    json_path = argv[0]
    project_id = argv[1]
    try:
        result = asyncio.run(_create_and_analyze(json_path, project_id))
        # Per requirement: return simple message
        print(result)
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == '__main__':
    main()

