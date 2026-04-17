from __future__ import annotations

from typing import Any

import pytest

from app.features.projects.application.workspace_composer import ProjectWorkspaceComposer


class StubWorkspaceRepository:
    async def get_workspace_seed(
        self,
        *,
        project_id: str,
        db: object,
    ) -> dict[str, object] | None:
        assert project_id == "project-123"
        assert db == "db-session"
        return {
            "project": {
                "id": project_id,
                "name": "Contoso Landing Zone",
                "createdAt": "2026-04-01T10:00:00Z",
                "textRequirements": "Build an Azure landing zone",
            },
            "documentCount": 2,
            "messageCount": 3,
            "threadCount": 1,
            "lastMessageAt": "2026-04-01T11:00:00Z",
        }


class StubStateProvider:
    async def get_project_state(self, project_id: str, db: object) -> dict[str, Any]:
        assert project_id == "project-123"
        assert db == "db-session"
        return {
            "projectId": project_id,
            "context": {"summary": "Composed state", "targetUsers": "Architects"},
            "applicationStructure": {"components": ["api"]},
            "openQuestions": ["What is the RTO?"],
            "requirements": [{"id": "req-1", "text": "Keep behavior stable"}],
            "referenceDocuments": [{"id": "doc-1", "title": "Reference Architecture"}],
            "projectDocumentStats": {
                "attemptedDocuments": 1,
                "parsedDocuments": 1,
                "failedDocuments": 0,
                "failures": [],
            },
            "lastUpdated": "2026-04-01T12:00:00Z",
            "diagrams": [{"diagramSetId": "ds-1", "diagramTypes": ["context"]}],
        }


class StubArchitectureInputsProvider:
    async def get_architecture_inputs(
        self,
        *,
        project_id: str,
        db: object,
    ) -> dict[str, Any] | None:
        assert project_id == "project-123"
        assert db == "db-session"
        return {"nfrs": {"availability": "99.95%"}}


class StubChecklistProvider:
    async def list_checklists(self, *, project_id: str, db: object) -> list[dict[str, Any]]:
        assert project_id == "project-123"
        assert db == "db-session"
        return []


class StubKnowledgeProvider:
    def list_knowledge_bases(self) -> list[dict[str, Any]]:
        return []


class StubSettingsProvider:
    def get_current_provider(self) -> str:
        return "copilot"

    def get_current_model(self) -> str:
        return "gpt-5.4"


@pytest.mark.asyncio
async def test_workspace_composer_returns_structured_workspace_view() -> None:
    composer = ProjectWorkspaceComposer(
        repository=StubWorkspaceRepository(),
        state_provider=StubStateProvider(),
        architecture_inputs_provider=StubArchitectureInputsProvider(),
        checklist_provider=StubChecklistProvider(),
        knowledge_provider=StubKnowledgeProvider(),
        settings_provider=StubSettingsProvider(),
    )

    workspace = await composer.compose(project_id="project-123", db="db-session")

    assert workspace.project.id == "project-123"
    assert workspace.inputs.context == {"summary": "Composed state", "targetUsers": "Architects"}
    assert workspace.inputs.nfrs == {"availability": "99.95%"}
    assert workspace.documents.items == [{"id": "doc-1", "title": "Reference Architecture"}]
    assert workspace.artifacts.requirements == [{"id": "req-1", "text": "Keep behavior stable"}]
    assert workspace.state.artifact_keys == [
        "applicationStructure",
        "context",
        "nfrs",
        "openQuestions",
        "projectDocumentStats",
        "referenceDocuments",
        "requirements",
    ]
    assert workspace.diagrams[0].diagram_set_id == "ds-1"

    dumped = workspace.model_dump(by_alias=True)
    assert "projectState" not in dumped
    assert dumped["inputs"]["context"] == {"summary": "Composed state", "targetUsers": "Architects"}
    assert dumped["documents"]["items"] == [{"id": "doc-1", "title": "Reference Architecture"}]
    assert dumped["artifacts"]["requirements"] == [{"id": "req-1", "text": "Keep behavior stable"}]
