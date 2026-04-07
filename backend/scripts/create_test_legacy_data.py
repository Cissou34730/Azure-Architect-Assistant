
import asyncio
import json
import sys
import uuid
from importlib import import_module
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

project_models = import_module("app.models.project")
projects_database = import_module("app.shared.db.projects_database")
Project = project_models.Project
ProjectState = project_models.ProjectState
AsyncSessionLocal = projects_database.AsyncSessionLocal


async def create_data():
    session_factory = AsyncSessionLocal

    async with session_factory() as session:
        # 1. Create a project
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            name="Legacy Project",
            text_requirements="Testing backfill"
        )
        session.add(project)

        # 2. Create legacy ProjectState
        legacy_state = {
            "wafChecklist": {
                "slug": "waf-2024",
                "items": [
                    {
                        "id": "reliability-1",
                        "title": "Design for high availability",
                        "status": "fixed",
                        "pillar": "reliability"
                    },
                    {
                        "id": "security-1",
                        "title": "Use Azure RBAC",
                        "status": "open",
                        "pillar": "security"
                    }
                ]
            }
        }

        state = ProjectState(
            project_id=project_id,
            state=json.dumps(legacy_state)
        )
        session.add(state)

        await session.commit()
        print(f"Created legacy project {project_id}")

if __name__ == "__main__":
    asyncio.run(create_data())
