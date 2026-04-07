"""Workspace composition for the projects feature."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, cast

from app.features.checklists.contracts import ChecklistSummaryContract
from app.features.diagrams.contracts import DiagramSummaryContract
from app.features.knowledge.contracts import KnowledgeBaseSummaryContract
from app.features.projects.contracts import (
    AgentWorkspaceSummary,
    ProjectWorkspaceArtifacts,
    ProjectWorkspaceDocuments,
    ProjectWorkspaceInputs,
    ProjectWorkspaceProjectSummary,
    ProjectWorkspaceSettingsSummary,
    ProjectWorkspaceStateSummary,
    ProjectWorkspaceView,
)
from app.features.projects.infrastructure.architecture_inputs_repository import (
    merge_architecture_inputs,
)


class WorkspaceRepository(Protocol):
    async def get_workspace_seed(
        self,
        *,
        project_id: str,
        db: object,
    ) -> dict[str, Any] | None: ...


class StateProvider(Protocol):
    async def get_project_state(self, project_id: str, db: object) -> dict[str, Any]: ...


class ChecklistProvider(Protocol):
    async def list_checklists(self, *, project_id: str, db: object) -> list[dict[str, Any]]: ...


class ArchitectureInputsProvider(Protocol):
    async def get_architecture_inputs(
        self,
        *,
        project_id: str,
        db: object,
    ) -> dict[str, Any] | None: ...


class KnowledgeProvider(Protocol):
    def list_knowledge_bases(self) -> list[dict[str, Any]]: ...


class SettingsProvider(Protocol):
    def get_current_provider(self) -> str: ...

    def get_current_model(self) -> str: ...


@dataclass(frozen=True)
class _WorkspaceProviders:
    state_provider: StateProvider
    architecture_inputs_provider: ArchitectureInputsProvider
    checklist_provider: ChecklistProvider
    knowledge_provider: KnowledgeProvider


_REQUIRED_PROVIDER_KEYS = frozenset(
    {
        "state_provider",
        "architecture_inputs_provider",
        "checklist_provider",
        "knowledge_provider",
    }
)
_EXCLUDED_ARTIFACT_KEYS = frozenset({"projectId", "lastUpdated", "diagrams", "wafChecklist"})


class ProjectWorkspaceComposer:
    """Compose a project workspace view from project and cross-feature sources."""

    def __init__(
        self,
        *,
        repository: WorkspaceRepository,
        settings_provider: SettingsProvider,
        **providers: object,
    ) -> None:
        resolved_providers = _build_workspace_providers(providers)
        self._repository = repository
        self._state_provider = resolved_providers.state_provider
        self._architecture_inputs_provider = resolved_providers.architecture_inputs_provider
        self._checklist_provider = resolved_providers.checklist_provider
        self._knowledge_provider = resolved_providers.knowledge_provider
        self._settings_provider = settings_provider

    async def compose(self, *, project_id: str, db: object) -> ProjectWorkspaceView:
        workspace_seed = await self._repository.get_workspace_seed(project_id=project_id, db=db)
        if workspace_seed is None:
            raise ValueError("Project not found")

        project_state = await self._safe_get_project_state(project_id=project_id, db=db)
        architecture_inputs = await self._safe_get_architecture_inputs(project_id=project_id, db=db)
        project_state = merge_architecture_inputs(project_state, architecture_inputs)
        project_state.setdefault("projectId", project_id)
        checklist_payloads = await self._checklist_provider.list_checklists(
            project_id=project_id,
            db=db,
        )
        knowledge_base_payloads = self._knowledge_provider.list_knowledge_bases()

        project_payload = workspace_seed["project"]
        state_last_updated = self._stringify(project_state.get("lastUpdated"))
        diagrams = self._extract_diagrams(project_state)
        artifact_keys = sorted(
            key for key in project_state if key not in _EXCLUDED_ARTIFACT_KEYS
        )

        return ProjectWorkspaceView(
            project=ProjectWorkspaceProjectSummary(
                id=str(project_payload["id"]),
                name=str(project_payload["name"]),
                created_at=str(project_payload["createdAt"]),
                text_requirements=str(project_payload.get("textRequirements") or ""),
                document_count=int(workspace_seed.get("documentCount", 0)),
            ),
            state=ProjectWorkspaceStateSummary(
                last_updated=state_last_updated,
                artifact_keys=artifact_keys,
            ),
            inputs=ProjectWorkspaceInputs(
                context=self._dict_value(project_state.get("context")),
                nfrs=self._optional_dict(project_state.get("nfrs")),
                application_structure=self._optional_dict(project_state.get("applicationStructure")),
                data_compliance=self._optional_dict(project_state.get("dataCompliance")),
                technical_constraints=self._optional_dict(project_state.get("technicalConstraints")),
                open_questions=self._list_value(project_state.get("openQuestions")),
            ),
            documents=ProjectWorkspaceDocuments(
                items=self._list_of_dicts(project_state.get("referenceDocuments")),
                stats=self._optional_dict(project_state.get("projectDocumentStats")),
            ),
            artifacts=ProjectWorkspaceArtifacts(
                requirements=self._list_of_dicts(project_state.get("requirements")),
                assumptions=self._list_of_dicts(project_state.get("assumptions")),
                clarification_questions=self._list_of_dicts(project_state.get("clarificationQuestions")),
                candidate_architectures=self._list_of_dicts(project_state.get("candidateArchitectures")),
                adrs=self._list_of_dicts(project_state.get("adrs")),
                findings=self._list_of_dicts(project_state.get("findings")),
                diagrams=self._list_of_dicts(project_state.get("diagrams")),
                iac_artifacts=self._list_of_dicts(project_state.get("iacArtifacts")),
                cost_estimates=self._list_of_dicts(project_state.get("costEstimates")),
                traceability_links=self._list_of_dicts(project_state.get("traceabilityLinks")),
                traceability_issues=self._list_of_dicts(project_state.get("traceabilityIssues")),
                mind_map_coverage=self._optional_dict(project_state.get("mindMapCoverage")),
                mind_map=self._optional_dict(project_state.get("mindMap")),
                mcp_queries=self._list_of_dicts(project_state.get("mcpQueries")),
                iteration_events=self._list_of_dicts(project_state.get("iterationEvents")),
                analysis_summary=self._optional_dict(project_state.get("analysisSummary")),
                waf_checklist=self._optional_dict(project_state.get("wafChecklist")),
            ),
            agent=AgentWorkspaceSummary(
                message_count=int(workspace_seed.get("messageCount", 0)),
                thread_count=int(workspace_seed.get("threadCount", 0)),
                last_message_at=self._stringify(workspace_seed.get("lastMessageAt")),
            ),
            checklists=[
                ChecklistSummaryContract(
                    id=str(payload.get("id", "")),
                    title=str(payload.get("title", "")),
                    status=str(payload.get("status", "unknown")),
                    items_count=int(payload.get("items_count", payload.get("itemsCount", 0))),
                    last_synced_at=self._stringify(
                        payload.get("last_synced_at", payload.get("lastSyncedAt"))
                    ),
                )
                for payload in checklist_payloads
            ],
            knowledge_bases=[
                KnowledgeBaseSummaryContract(
                    id=str(payload.get("id", payload.get("kb_id", ""))),
                    name=str(payload.get("name", payload.get("kb_name", ""))),
                    status=str(payload.get("status", "unknown")),
                    profiles=[str(profile) for profile in payload.get("profiles", [])],
                    priority=int(payload.get("priority", 0)),
                )
                for payload in knowledge_base_payloads
            ],
            diagrams=diagrams,
            settings=ProjectWorkspaceSettingsSummary(
                provider=self._settings_provider.get_current_provider(),
                model=self._settings_provider.get_current_model(),
            ),
        )

    async def _safe_get_project_state(self, *, project_id: str, db: object) -> dict[str, Any]:
        try:
            return await self._state_provider.get_project_state(project_id, db)
        except ValueError:
            return {}

    async def _safe_get_architecture_inputs(
        self,
        *,
        project_id: str,
        db: object,
    ) -> dict[str, Any] | None:
        try:
            return await self._architecture_inputs_provider.get_architecture_inputs(
                project_id=project_id,
                db=db,
            )
        except ValueError:
            return None

    def _extract_diagrams(self, project_state: dict[str, Any]) -> list[DiagramSummaryContract]:
        raw_diagrams = project_state.get("diagrams")
        if not isinstance(raw_diagrams, list):
            return []

        diagrams: list[DiagramSummaryContract] = []
        for raw_diagram in raw_diagrams:
            if not isinstance(raw_diagram, dict):
                continue
            diagram_set_id = raw_diagram.get("diagramSetId")
            if not diagram_set_id:
                continue
            raw_types = raw_diagram.get("diagramTypes")
            diagram_types = [str(item) for item in raw_types] if isinstance(raw_types, list) else []
            diagrams.append(
                DiagramSummaryContract(
                    diagram_set_id=str(diagram_set_id),
                    diagram_types=diagram_types,
                )
            )
        return diagrams

    def _stringify(self, value: object) -> str | None:
        if value is None:
            return None
        return str(value)

    def _optional_dict(self, value: object) -> dict[str, Any] | None:
        return dict(value) if isinstance(value, dict) else None

    def _dict_value(self, value: object) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    def _list_value(self, value: object) -> list[Any]:
        return list(value) if isinstance(value, list) else []

    def _list_of_dicts(self, value: object) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [dict(item) for item in value if isinstance(item, dict)]


def _build_workspace_providers(providers: dict[str, object]) -> _WorkspaceProviders:
    provider_keys = set(providers)
    missing_keys = sorted(_REQUIRED_PROVIDER_KEYS - provider_keys)
    if missing_keys:
        raise TypeError(f"Missing workspace providers: {', '.join(missing_keys)}")

    unexpected_keys = sorted(provider_keys - _REQUIRED_PROVIDER_KEYS)
    if unexpected_keys:
        raise TypeError(f"Unexpected workspace providers: {', '.join(unexpected_keys)}")

    return _WorkspaceProviders(
        state_provider=cast(StateProvider, providers["state_provider"]),
        architecture_inputs_provider=cast(
            ArchitectureInputsProvider,
            providers["architecture_inputs_provider"],
        ),
        checklist_provider=cast(ChecklistProvider, providers["checklist_provider"]),
        knowledge_provider=cast(KnowledgeProvider, providers["knowledge_provider"]),
    )
