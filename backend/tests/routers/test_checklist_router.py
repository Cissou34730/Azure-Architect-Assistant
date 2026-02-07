import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.main import app
from app.projects_database import get_db
from app.models.checklist import Checklist, ChecklistItem
from app.models.project import Project, ProjectState

@pytest.fixture
async def async_client(test_db_session: AsyncSession):
    """
    Fixture for AsyncClient that overrides the get_db dependency.
    """
    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.fixture
async def sample_project(test_db_session: AsyncSession):
    """Create a sample project for testing."""
    project_id = str(uuid.uuid4())
    # Create Project
    project = Project(
        id=project_id,
        name="Test Project"
    )
    test_db_session.add(project)
    
    # Create ProjectState
    project_state = ProjectState(
        project_id=project_id,
        state='{"wafChecklist": {}}'
    )
    test_db_session.add(project_state)
    
    await test_db_session.commit()
    return project_id

@pytest.fixture
async def sample_checklist(test_db_session: AsyncSession, sample_project: str):
    """Create a sample checklist for testing."""
    checklist_id = uuid.uuid4()
    checklist = Checklist(
        id=checklist_id,
        project_id=sample_project,
        title="Reliability",
        status="open"
    )
    test_db_session.add(checklist)
    
    item = ChecklistItem(
        id=uuid.uuid4(),
        checklist_id=checklist_id,
        template_item_id="item-1",
        title="Sample Item",
        severity="medium"
    )
    test_db_session.add(item)
    
    await test_db_session.commit()
    return checklist_id

@pytest.mark.asyncio
async def test_get_checklists(async_client: AsyncClient, sample_project: str, sample_checklist: uuid.UUID):
    """Test retrieving lists of checklists for a project."""
    response = await async_client.get(f"/api/projects/{sample_project}/checklists")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(c["id"] == str(sample_checklist) for c in data)

@pytest.mark.asyncio
async def test_get_checklist_detail(async_client: AsyncClient, sample_project: str, sample_checklist: uuid.UUID):
    """Test retrieving details of a specific checklist."""
    response = await async_client.get(f"/api/projects/{sample_project}/checklists/{sample_checklist}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_checklist)
    assert len(data["items"]) >= 1

@pytest.mark.asyncio
async def test_evaluate_checklist_item(async_client: AsyncClient, sample_project: str, sample_checklist: uuid.UUID, test_db_session: AsyncSession):
    """Test evaluating a checklist item via API."""
    # Get the item ID first
    get_resp = await async_client.get(f"/api/projects/{sample_project}/checklists/{sample_checklist}")
    item_id = get_resp.json()["items"][0]["id"]
    
    # Evaluate it
    eval_resp = await async_client.post(
        f"/api/projects/{sample_project}/checklists/items/{item_id}/evaluate",
        json={"status": "fixed", "comment": "Test comment"}
    )
    assert eval_resp.status_code == 200
    assert eval_resp.json()["status"] == "success"
    
    # Verify in DB
    from sqlalchemy import select
    from app.models.checklist import ChecklistItemEvaluation
    # Clear session to ensure we read fresh from DB
    test_db_session.expire_all()
    res = await test_db_session.execute(
        select(ChecklistItemEvaluation).where(ChecklistItemEvaluation.item_id == uuid.UUID(item_id))
    )
    evaluation = res.scalar_one()
    assert evaluation.status == "fixed"
    assert evaluation.comment == "Test comment"

@pytest.mark.asyncio
async def test_get_progress(async_client: AsyncClient, sample_project: str, sample_checklist: uuid.UUID):
    """Test retrieving progress summary."""
    response = await async_client.get(f"/api/projects/{sample_project}/checklists/progress")
    if response.status_code == 422:
        print(f"Validation Error: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert "total_items" in data
    assert "completed_items" in data
    assert data["total_items"] >= 1


@pytest.mark.asyncio
async def test_list_checklists_bootstraps_default_template(
    async_client: AsyncClient, sample_project: str
):
    """If a project has no normalized checklists yet, endpoint bootstraps one."""
    response = await async_client.get(f"/api/projects/{sample_project}/checklists")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["items_count"] >= 1
