import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.app_settings import get_settings
from app.main import app
from app.models.checklist import Checklist, ChecklistItem
from app.models.project import ProjectState
from app.projects_database import get_db


@pytest.fixture
async def async_client(test_db_session: AsyncSession):
    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _write_template(cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "slug": "azure-waf-v1",
        "title": "Azure Well-Architected Framework",
        "version": "2024",
        "source": "tests",
        "source_url": "https://example.com/waf",
        "source_version": "2024",
        "content": {
            "items": [
                {
                    "id": "sec-01",
                    "title": "Secure admin access",
                    "pillar": "Security",
                    "severity": "high",
                },
                {
                    "id": "rel-01",
                    "title": "Backup and restore strategy",
                    "pillar": "Reliability",
                    "severity": "critical",
                },
            ]
        },
    }
    (cache_dir / "azure-waf-v1.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_create_project_bootstraps_state_and_waf_checklist(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    cache_dir = tmp_path / "checklists"
    _write_template(cache_dir)

    settings = get_settings().model_copy(deep=True)
    settings.aaa_feature_waf_normalized = True
    settings.waf_template_cache_dir = cache_dir

    monkeypatch.setattr(
        "app.routers.project_management.services.project_service.get_app_settings",
        lambda: settings,
    )

    response = await async_client.post("/api/projects", json={"name": "Bootstrap Project"})
    assert response.status_code == 200
    project_id = response.json()["project"]["id"]

    state_row = (
        await test_db_session.execute(
            select(ProjectState).where(ProjectState.project_id == project_id)
        )
    ).scalar_one_or_none()
    assert state_row is not None

    state_data = json.loads(state_row.state)
    waf = state_data.get("wafChecklist", {})
    assert isinstance(waf, dict)
    assert isinstance(waf.get("items"), list)
    assert len(waf["items"]) >= 2

    state_response = await async_client.get(f"/api/projects/{project_id}/state")
    assert state_response.status_code == 200
    state_payload = state_response.json()["projectState"]
    assert isinstance(state_payload.get("wafChecklist", {}).get("items"), list)
    assert len(state_payload["wafChecklist"]["items"]) >= 2

    checklist = (
        await test_db_session.execute(
            select(Checklist).where(Checklist.project_id == project_id)
        )
    ).scalar_one_or_none()
    assert checklist is not None

    items = (
        await test_db_session.execute(
            select(ChecklistItem).where(ChecklistItem.checklist_id == checklist.id)
        )
    ).scalars().all()
    assert len(items) >= 2
