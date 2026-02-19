"""Tests for project deletion endpoints (soft delete)."""

import json
import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models import Project
from app.models.diagram import DiagramSet
from app.models.project import ProjectState
from app.projects_database import get_db
from app.services.diagram.database import get_diagram_session


@pytest.fixture
async def async_client(test_db_session: AsyncSession):
    """Provide an async HTTP client with test database."""

    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_project_sets_deleted_at(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    """Test that deleting a project sets deleted_at timestamp."""
    project = Project(
        id="proj-del-1",
        name="Delete Test Project",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    test_db_session.add(project)
    await test_db_session.commit()

    response = await async_client.delete(f"/api/projects/{project.id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Project deleted successfully"
    assert payload["deletedCount"] == 1
    assert payload["projectIds"] == [project.id]

    # Verify project has deleted_at set
    result = await test_db_session.execute(
        select(Project).where(Project.id == project.id)
    )
    deleted_project = result.scalar_one()
    assert deleted_project.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_nonexistent_project_returns_404(
    async_client: AsyncClient,
) -> None:
    """Test that deleting a nonexistent project returns 404."""
    response = await async_client.delete("/api/projects/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deleted_projects_filtered_from_list(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    """Test that deleted projects don't appear in list endpoint."""
    project1 = Project(
        id="proj-list-1",
        name="Active Project",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    project2 = Project(
        id="proj-list-2",
        name="Deleted Project",
        created_at=datetime.now(timezone.utc).isoformat(),
        deleted_at=datetime.now(timezone.utc).isoformat(),
    )
    test_db_session.add_all([project1, project2])
    await test_db_session.commit()

    response = await async_client.get("/api/projects")
    assert response.status_code == 200
    payload = response.json()
    projects = payload["projects"]

    # Should only see the active project
    assert len(projects) == 1
    assert projects[0]["id"] == project1.id


@pytest.mark.asyncio
async def test_get_deleted_project_returns_404(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    """Test that getting a deleted project returns 404."""
    project = Project(
        id="proj-get-1",
        name="Deleted Project",
        created_at=datetime.now(timezone.utc).isoformat(),
        deleted_at=datetime.now(timezone.utc).isoformat(),
    )
    test_db_session.add(project)
    await test_db_session.commit()

    response = await async_client.get(f"/api/projects/{project.id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_bulk_delete_projects(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    """Test bulk deletion of multiple projects."""
    projects = [
        Project(
            id=f"proj-bulk-{i}",
            name=f"Bulk Project {i}",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        for i in range(3)
    ]
    test_db_session.add_all(projects)
    await test_db_session.commit()

    project_ids = [p.id for p in projects]
    response = await async_client.post(
        "/api/projects/bulk-delete",
        json={"projectIds": project_ids},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["deletedCount"] == 3
    assert set(payload["projectIds"]) == set(project_ids)

    # Verify all projects have deleted_at set
    for project_id in project_ids:
        result = await test_db_session.execute(
            select(Project).where(Project.id == project_id)
        )
        deleted_project = result.scalar_one()
        assert deleted_project.deleted_at is not None


@pytest.mark.asyncio
async def test_bulk_delete_ignores_already_deleted(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    """Test that bulk delete ignores already deleted projects."""
    project1 = Project(
        id="proj-bulk-active",
        name="Active Project",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    project2 = Project(
        id="proj-bulk-deleted",
        name="Already Deleted Project",
        created_at=datetime.now(timezone.utc).isoformat(),
        deleted_at=datetime.now(timezone.utc).isoformat(),
    )
    test_db_session.add_all([project1, project2])
    await test_db_session.commit()

    response = await async_client.post(
        "/api/projects/bulk-delete",
        json={"projectIds": [project1.id, project2.id]},
    )
    assert response.status_code == 200
    payload = response.json()
    # Should only delete the active project
    assert payload["deletedCount"] == 1
    assert payload["projectIds"] == [project1.id]


@pytest.mark.asyncio
async def test_bulk_delete_with_nonexistent_projects(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    """Test that bulk delete handles nonexistent projects gracefully."""
    project = Project(
        id="proj-exists",
        name="Exists Project",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    test_db_session.add(project)
    await test_db_session.commit()

    response = await async_client.post(
        "/api/projects/bulk-delete",
        json={"projectIds": [project.id, "nonexistent-1", "nonexistent-2"]},
    )
    assert response.status_code == 200
    payload = response.json()
    # Should only delete the existing project
    assert payload["deletedCount"] == 1
    assert payload["projectIds"] == [project.id]


@pytest.mark.asyncio
async def test_bulk_delete_empty_list(
    async_client: AsyncClient,
) -> None:
    """Test that bulk delete with empty list returns zero deletions."""
    response = await async_client.post(
        "/api/projects/bulk-delete",
        json={"projectIds": []},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["deletedCount"] == 0
    assert payload["projectIds"] == []


@pytest.mark.asyncio
async def test_delete_project_cleans_up_diagram_references(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that deleting a project attempts to clean up diagram sets."""
    project = Project(
        id="proj-diagram-cleanup",
        name="Project with Diagrams",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    test_db_session.add(project)

    # Create project state with diagram references
    diagram_set_id = str(uuid.uuid4())
    state_data = {
        "diagrams": [
            {
                "id": str(uuid.uuid4()),
                "diagramSetId": diagram_set_id,
                "type": "c4_context",
            }
        ]
    }
    state = ProjectState(
        project_id=project.id,
        state=json.dumps(state_data),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    test_db_session.add(state)
    await test_db_session.commit()

    # Mock diagram cleanup to track if it was called
    cleanup_called = []

    async def mock_diagram_session():
        class MockSession:
            async def execute(self, *args, **kwargs):
                cleanup_called.append(True)
                return None

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        yield MockSession()

    monkeypatch.setattr(
        "app.routers.project_management.services.project_service.get_diagram_session",
        mock_diagram_session,
    )

    response = await async_client.delete(f"/api/projects/{project.id}")
    assert response.status_code == 200

    # Verify diagram cleanup was attempted
    assert len(cleanup_called) > 0
