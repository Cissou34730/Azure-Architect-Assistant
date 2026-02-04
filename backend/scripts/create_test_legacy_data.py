
import asyncio
import uuid
import json
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

from app.projects_database import AsyncSessionLocal
from app.models.project import Project, ProjectState

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
