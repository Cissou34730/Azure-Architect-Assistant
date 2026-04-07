"""Workspace-specific dependency wiring for the projects API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from app.features.checklists.application.api_service import ChecklistsApiService
from app.features.checklists.infrastructure.service import ChecklistService
from app.features.knowledge.application.management_orchestration_service import KBManagementService
from app.features.knowledge.infrastructure import KBManager
from app.features.projects.application.workspace_composer import ProjectWorkspaceComposer
from app.features.projects.infrastructure import (
    ProjectArchitectureInputsRepository,
    ProjectWorkspaceRepository,
)
from app.features.settings.application.settings_service import SettingsModelsService


class _ChecklistWorkspaceAdapter:
    def __init__(
        self,
        *,
        api_service: ChecklistsApiService,
        checklist_service: ChecklistService,
    ) -> None:
        self._api_service = api_service
        self._checklist_service = checklist_service

    async def list_checklists(self, *, project_id: str, db: Any) -> list[dict[str, Any]]:
        return await self._api_service.list_checklists(
            project_id=project_id,
            db=db,
            checklist_service=self._checklist_service,
        )


class _KnowledgeWorkspaceAdapter:
    def __init__(
        self,
        *,
        management_service: KBManagementService,
        kb_manager: KBManager,
    ) -> None:
        self._management_service = management_service
        self._kb_manager = kb_manager

    def list_knowledge_bases(self) -> list[dict[str, Any]]:
        return self._management_service.list_knowledge_bases(self._kb_manager)


class _ArchitectureInputsWorkspaceAdapter:
    def __init__(self, *, repository: ProjectArchitectureInputsRepository) -> None:
        self._repository = repository

    async def get_architecture_inputs(
        self,
        *,
        project_id: str,
        db: Any,
    ) -> dict[str, Any] | None:
        return await self._repository.get_architecture_inputs(project_id=project_id, db=db)


@dataclass(frozen=True)
class _WorkspaceComposerCollaborators:
    architecture_inputs_provider: _ArchitectureInputsWorkspaceAdapter
    checklist_provider: _ChecklistWorkspaceAdapter
    knowledge_provider: _KnowledgeWorkspaceAdapter


_REQUIRED_COLLABORATOR_KEYS = frozenset(
    {
        "architecture_inputs_repository",
        "checklists_api_service",
        "checklist_service",
        "kb_management_service",
        "kb_manager",
    }
)


def create_workspace_composer(
    *,
    repository: ProjectWorkspaceRepository,
    state_provider: Any,
    settings_service: SettingsModelsService,
    **collaborator_dependencies: Any,
) -> ProjectWorkspaceComposer:
    collaborators = _build_workspace_collaborators(collaborator_dependencies)
    return ProjectWorkspaceComposer(
        repository=repository,
        settings_provider=settings_service,
        state_provider=state_provider,
        architecture_inputs_provider=collaborators.architecture_inputs_provider,
        checklist_provider=collaborators.checklist_provider,
        knowledge_provider=collaborators.knowledge_provider,
    )


def _build_workspace_collaborators(
    collaborator_dependencies: dict[str, Any],
) -> _WorkspaceComposerCollaborators:
    collaborator_keys = set(collaborator_dependencies)
    missing_keys = sorted(_REQUIRED_COLLABORATOR_KEYS - collaborator_keys)
    if missing_keys:
        raise TypeError(f"Missing workspace collaborator dependencies: {', '.join(missing_keys)}")

    unexpected_keys = sorted(collaborator_keys - _REQUIRED_COLLABORATOR_KEYS)
    if unexpected_keys:
        raise TypeError(
            f"Unexpected workspace collaborator dependencies: {', '.join(unexpected_keys)}"
        )

    return _WorkspaceComposerCollaborators(
        architecture_inputs_provider=_ArchitectureInputsWorkspaceAdapter(
            repository=cast(
                ProjectArchitectureInputsRepository,
                collaborator_dependencies["architecture_inputs_repository"],
            )
        ),
        checklist_provider=_ChecklistWorkspaceAdapter(
            api_service=cast(
                ChecklistsApiService,
                collaborator_dependencies["checklists_api_service"],
            ),
            checklist_service=cast(
                ChecklistService,
                collaborator_dependencies["checklist_service"],
            ),
        ),
        knowledge_provider=_KnowledgeWorkspaceAdapter(
            management_service=cast(
                KBManagementService,
                collaborator_dependencies["kb_management_service"],
            ),
            kb_manager=cast(KBManager, collaborator_dependencies["kb_manager"]),
        ),
    )
