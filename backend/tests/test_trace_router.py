from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.projects.api.trace_router import get_trace_service_dep, router
from app.features.projects.contracts.trace import ProjectTraceEventsResponse
from app.shared.db.projects_database import get_db


class _TraceServiceStub:
    async def list_events(
        self,
        *,
        project_id: str,
        db: object,
        limit: int,
        thread_id: str | None,
    ) -> ProjectTraceEventsResponse:
        assert project_id == "project-123"
        assert db == "db-session"
        assert limit == 25
        assert thread_id == "thread-1"
        return ProjectTraceEventsResponse.model_validate(
            {
                "events": [
                    {
                        "id": "evt-1",
                        "projectId": "project-123",
                        "threadId": "thread-1",
                        "eventType": "workflow_stage_result",
                        "payload": {
                            "stage": "propose_candidate",
                            "changeSetId": "pcs-1",
                        },
                        "createdAt": "2026-04-17T10:00:00Z",
                    }
                ]
            }
        )


def test_trace_route_returns_project_trace_timeline() -> None:
    app = FastAPI()
    app.include_router(router)

    async def _get_db_override():
        yield "db-session"

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_trace_service_dep] = lambda: _TraceServiceStub()

    with TestClient(app) as client:
        response = client.get("/api/projects/project-123/trace?thread_id=thread-1&limit=25")

    assert response.status_code == 200
    assert response.json() == {
        "events": [
            {
                "id": "evt-1",
                "projectId": "project-123",
                "threadId": "thread-1",
                "eventType": "workflow_stage_result",
                "payload": {
                    "stage": "propose_candidate",
                    "changeSetId": "pcs-1",
                },
                "createdAt": "2026-04-17T10:00:00Z",
            }
        ]
    }
