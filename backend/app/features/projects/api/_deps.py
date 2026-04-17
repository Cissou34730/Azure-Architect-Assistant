"""Shared service factories for the projects feature."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.dependencies import (
    get_kb_management_service_dependency,
    get_kb_manager,
    get_multi_query_service_dependency,
)
from app.features.agent.application import RequirementsExtractionWorker
from app.features.checklists.application.api_service import ChecklistsApiService
from app.features.checklists.domain.default_templates import resolve_bootstrap_template_slugs
from app.features.checklists.infrastructure.engine import ChecklistEngine
from app.features.checklists.infrastructure.models import Checklist, ChecklistItem
from app.features.checklists.infrastructure.registry import ChecklistRegistry
from app.features.checklists.infrastructure.service import ChecklistService, get_checklist_service
from app.features.diagrams.application.database import get_diagram_session
from app.features.diagrams.application.project_diagram_helpers import (
    append_diagram_reference_to_project_state,
    ensure_initial_c4_context_diagram,
)
from app.features.diagrams.infrastructure.models import DiagramSet
from app.features.knowledge.application.management_orchestration_service import KBManagementService
from app.features.knowledge.application.query_service import QueryProfile
from app.features.knowledge.infrastructure import KBManager
from app.features.projects.api.workspace_dependencies import create_workspace_composer
from app.features.projects.application.chat_service import ChatService
from app.features.projects.application.document_content_service import DocumentContentService
from app.features.projects.application.document_service import DocumentService
from app.features.projects.application.pending_changes_service import (
    ProjectPendingChangesService,
)
from app.features.projects.application.project_analysis_service import ProjectAnalysisService
from app.features.projects.application.project_notes_service import ProjectNotesService
from app.features.projects.application.project_service import ProjectService
from app.features.projects.application.quality_gate_service import (
    ProjectTraceSummaryProvider,
    QualityGateService,
)
from app.features.projects.application.trace_service import ProjectTraceService
from app.features.projects.application.requirements_extraction_entry_service import (
    ProjectRequirementsExtractionEntryService,
)
from app.features.projects.application.state_edit_service import ProjectStateEditService
from app.features.projects.infrastructure import (
    ProjectArchitectureInputsRepository,
    ProjectWorkspaceRepository,
)
from app.features.settings.application.settings_service import SettingsModelsService
from app.shared.config.app_settings import get_app_settings


class _DiagramBootstrapperAdapter:
    async def ensure_initial_context_diagram(
        self,
        project_id: str,
        state: dict[str, Any],
    ) -> dict[str, Any] | None:
        return await ensure_initial_c4_context_diagram(project_id, state)

    async def append_diagram_reference(
        self,
        project_id: str,
        state: dict[str, Any],
        diagram_ref: dict[str, Any],
        db: Any,
    ) -> dict[str, Any]:
        return await append_diagram_reference_to_project_state(
            project_id,
            state,
            diagram_ref,
            db,
        )


class _KnowledgeChatQueryAdapter:
    def __init__(self, query_service: Any) -> None:
        self._query_service = query_service

    def query_chat_sources(self, message: str, *, top_k_per_kb: int = 3) -> list[dict[str, Any]]:
        kb_res = self._query_service.query_profile(
            question=message,
            profile=QueryProfile.CHAT,
            top_k_per_kb=top_k_per_kb,
        )
        return kb_res.get("sources", []) if kb_res.get("has_results") else []


async def _delete_diagram_sets(diagram_session: Any, diagram_set_ids: list[str]) -> None:
    await diagram_session.execute(
        delete(DiagramSet).where(DiagramSet.id.in_(diagram_set_ids))
    )


class _ChecklistProjectGateway:
    async def bootstrap_project_checklists(self, project_id: str, db: Any) -> None:
        settings = get_app_settings()

        @asynccontextmanager
        async def session_factory() -> AsyncIterator[Any]:
            yield db

        registry = ChecklistRegistry(Path(settings.waf_template_cache_dir), settings)
        engine = ChecklistEngine(session_factory, registry, settings)

        selected_slugs = resolve_bootstrap_template_slugs(
            [template.slug for template in registry.list_templates()]
        )
        checklists = await engine.ensure_project_checklists(
            project_id,
            selected_slugs if selected_slugs else None,
        )
        if not checklists:
            return

    async def get_waf_checklist_state(
        self,
        project_id: str,
        db: Any,
    ) -> dict[str, Any] | None:
        result = await db.execute(
            select(Checklist)
            .where(Checklist.project_id == project_id)
            .options(selectinload(Checklist.items).selectinload(ChecklistItem.evaluations))
        )
        checklists = result.scalars().all()
        if not checklists:
            return None

        items: list[dict[str, Any]] = []
        for checklist in checklists:
            for item in checklist.items:
                items.append(
                    {
                        "id": item.template_item_id,
                        "title": item.title,
                        "description": item.description,
                        "pillar": item.pillar,
                        "severity": item.severity.value if hasattr(item.severity, "value") else item.severity,
                    }
                )

        return {"items": items}


_checklist_project_gateway = _ChecklistProjectGateway()


_project_service = ProjectService(
    diagram_session_factory=get_diagram_session,
    delete_diagram_sets=_delete_diagram_sets,
    bootstrap_checklists=_checklist_project_gateway.bootstrap_project_checklists,
    get_checklist_state=_checklist_project_gateway.get_waf_checklist_state,
)
_document_service = DocumentService()
_document_content_service = DocumentContentService()
_project_analysis_service = ProjectAnalysisService(
    _document_service,
    diagram_bootstrapper=_DiagramBootstrapperAdapter(),
)
_chat_service = ChatService(
    project_service=_project_service,
    knowledge_query_gateway=_KnowledgeChatQueryAdapter(get_multi_query_service_dependency()),
)
_pending_changes_service = ProjectPendingChangesService(state_provider=_chat_service)
_quality_gate_service = QualityGateService(
    state_provider=_chat_service,
    trace_summary_provider=ProjectTraceSummaryProvider(),
)
_trace_service = ProjectTraceService()
_requirements_extraction_entry_service = ProjectRequirementsExtractionEntryService(
    worker=RequirementsExtractionWorker(
        pending_change_recorder=_pending_changes_service,
    )
)
_project_notes_service = ProjectNotesService()
_project_state_edit_service = ProjectStateEditService()
_checklists_api_service = ChecklistsApiService()
_settings_models_service = SettingsModelsService()
_architecture_inputs_repository = ProjectArchitectureInputsRepository()
_workspace_repository = ProjectWorkspaceRepository()


def get_project_service_dep() -> ProjectService:
    return _project_service


def get_document_service_dep() -> DocumentService:
    return _document_service


def get_document_content_service_dep() -> DocumentContentService:
    return _document_content_service


def get_project_analysis_service_dep() -> ProjectAnalysisService:
    return _project_analysis_service


def get_chat_service_dep() -> ChatService:
    return _chat_service


def get_state_edit_service_dep() -> ProjectStateEditService:
    return _project_state_edit_service


def get_project_notes_service_dep() -> ProjectNotesService:
    return _project_notes_service


def get_pending_changes_service_dep() -> ProjectPendingChangesService:
    return _pending_changes_service


def get_quality_gate_service_dep() -> QualityGateService:
    return _quality_gate_service


def get_trace_service_dep() -> ProjectTraceService:
    return _trace_service


def get_requirements_extraction_entry_service_dep() -> ProjectRequirementsExtractionEntryService:
    return _requirements_extraction_entry_service


async def get_workspace_composer_dep(
    checklist_service: ChecklistService = Depends(get_checklist_service),
    kb_manager: KBManager = Depends(get_kb_manager),
    kb_management_service: KBManagementService = Depends(get_kb_management_service_dependency),
) -> Any:
    return create_workspace_composer(
        repository=_workspace_repository,
        state_provider=_chat_service,
        architecture_inputs_repository=_architecture_inputs_repository,
        checklists_api_service=_checklists_api_service,
        checklist_service=checklist_service,
        kb_management_service=kb_management_service,
        kb_manager=kb_manager,
        settings_service=_settings_models_service,
    )

