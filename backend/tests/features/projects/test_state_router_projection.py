from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.projects.api.state_router import get_workspace_composer_dep, router
from app.features.projects.contracts.workspace import (
    AgentWorkspaceSummary,
    ProjectWorkspaceArtifacts,
    ProjectWorkspaceDocuments,
    ProjectWorkspaceInputs,
    ProjectWorkspaceProjectSummary,
    ProjectWorkspaceSettingsSummary,
    ProjectWorkspaceStateSummary,
    ProjectWorkspaceView,
)
from app.shared.db.projects_database import get_db


class StubWorkspaceComposer:
    async def compose(self, *, project_id: str, db: object) -> ProjectWorkspaceView:
        assert project_id == "project-123"
        assert db == "db-session"
        return ProjectWorkspaceView(
            project=ProjectWorkspaceProjectSummary(
                id=project_id,
                name="Contoso Landing Zone",
                created_at="2026-04-01T10:00:00Z",
                text_requirements="Build an Azure landing zone",
                document_count=2,
            ),
            state=ProjectWorkspaceStateSummary(
                last_updated="2026-04-01T12:00:00Z",
                artifact_keys=["applicationStructure", "openQuestions"],
            ),
            inputs=ProjectWorkspaceInputs(
                context={"summary": "Composed state"},
                application_structure={"components": ["api"]},
                open_questions=["What is the RTO?"],
            ),
            documents=ProjectWorkspaceDocuments(
                items=[{"id": "doc-1", "title": "Reference Architecture"}],
                stats={
                    "attemptedDocuments": 1,
                    "parsedDocuments": 1,
                    "failedDocuments": 0,
                    "failures": [],
                },
            ),
            artifacts=ProjectWorkspaceArtifacts(
                requirements=[{"id": "req-1", "text": "Keep behavior stable"}],
            ),
            agent=AgentWorkspaceSummary(
                message_count=3,
                thread_count=1,
                last_message_at="2026-04-01T11:00:00Z",
            ),
            checklists=[],
            knowledge_bases=[],
            diagrams=[],
            settings=ProjectWorkspaceSettingsSummary(provider="copilot", model="gpt-5.4"),
        )


def test_get_project_state_projects_structured_workspace_into_legacy_payload() -> None:
    app = FastAPI()
    app.include_router(router)

    async def get_db_override():
        yield "db-session"

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_workspace_composer_dep] = lambda: StubWorkspaceComposer()

    client = TestClient(app)
    response = client.get("/api/projects/project-123/state")

    assert response.status_code == 200
    assert response.headers["Deprecation"] == "true"
    assert response.headers["Sunset"] == "2026-06-01"
    assert response.headers["Link"] == '</api/projects/project-123/workspace>; rel="successor-version"'
    assert response.json() == {
        "projectState": {
            "projectId": "project-123",
            "lastUpdated": "2026-04-01T12:00:00Z",
            "context": {"summary": "Composed state"},
            "openQuestions": ["What is the RTO?"],
            "requirements": [{"id": "req-1", "text": "Keep behavior stable"}],
            "assumptions": [],
            "clarificationQuestions": [],
            "candidateArchitectures": [],
            "adrs": [],
            "findings": [],
            "diagrams": [],
            "iacArtifacts": [],
            "costEstimates": [],
            "traceabilityLinks": [],
            "traceabilityIssues": [],
            "mindMapCoverage": None,
            "mindMap": None,
            "referenceDocuments": [{"id": "doc-1", "title": "Reference Architecture"}],
            "projectDocumentStats": {
                "attemptedDocuments": 1,
                "parsedDocuments": 1,
                "failedDocuments": 0,
                "failures": [],
            },
            "analysisSummary": None,
            "mcpQueries": [],
            "iterationEvents": [],
            "wafChecklist": None,
            "applicationStructure": {"components": ["api"]},
            "ingestionStats": {
                "attemptedDocuments": 1,
                "parsedDocuments": 1,
                "failedDocuments": 0,
                "failures": [],
            },
            "summary": "Composed state",
        }
    }