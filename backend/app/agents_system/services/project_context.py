"""
Project context services for agent system.
Provides read/write access to ProjectState from database.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import Project, ProjectDocument, ProjectState
from .aaa_state_models import AAAProjectState, apply_us6_enrichment, ensure_aaa_defaults
from .mindmap_loader import is_mindmap_initialized, update_mindmap_coverage
from .state_update_parser import merge_state_updates_no_overwrite

logger = logging.getLogger(__name__)


def _normalize_parse_status(document: ProjectDocument) -> str:
    if document.parse_status is not None and document.parse_status != "":
        return document.parse_status
    return "parsed" if (document.raw_text or "").strip() else "parse_failed"


def _normalize_analysis_status(document: ProjectDocument) -> str:
    if document.analysis_status is not None and document.analysis_status != "":
        return document.analysis_status
    return "not_started" if (document.raw_text or "").strip() else "skipped"


def _document_to_reference_payload(document: ProjectDocument) -> dict[str, Any]:
    return {
        "id": document.id,
        "category": "uploaded",
        "title": document.file_name,
        "url": f"/api/projects/{document.project_id}/documents/{document.id}/content"
        if document.stored_path
        else None,
        "mimeType": document.mime_type,
        "accessedAt": document.uploaded_at,
        "parseStatus": _normalize_parse_status(document),
        "analysisStatus": _normalize_analysis_status(document),
        "parseError": document.parse_error,
        "uploadedAt": document.uploaded_at,
        "analyzedAt": document.analyzed_at,
    }


def _compute_project_document_stats(documents: list[ProjectDocument]) -> dict[str, Any]:
    parsed_documents = 0
    failures: list[dict[str, Any]] = []
    for document in documents:
        parse_status = _normalize_parse_status(document)
        if parse_status == "parsed":
            parsed_documents += 1
            continue
        failures.append(
            {
                "documentId": document.id,
                "fileName": document.file_name,
                "reason": document.parse_error or "no extractable text",
            }
        )
    return {
        "attemptedDocuments": len(documents),
        "parsedDocuments": parsed_documents,
        "failedDocuments": max(len(documents) - parsed_documents, 0),
        "failures": failures,
    }


def _merge_uploaded_reference_documents(
    current_reference_documents: Any,
    uploaded_reference_documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged_by_id: dict[str, dict[str, Any]] = {}

    if isinstance(current_reference_documents, list):
        for item in current_reference_documents:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id") or "").strip()
            if item_id == "":
                continue
            merged_by_id[item_id] = dict(item)

    for uploaded_document in uploaded_reference_documents:
        merged_by_id[uploaded_document["id"]] = uploaded_document

    return list(merged_by_id.values())


async def read_project_state(
    project_id: str, db: AsyncSession
) -> dict[str, Any] | None:
    """
    Read ProjectState from database.

    Args:
        project_id: Project ID
        db: Database session

    Returns:
        ProjectState dictionary or None if not found
    """
    result = await db.execute(
        select(ProjectState).where(ProjectState.project_id == project_id)
    )
    state_record = result.scalar_one_or_none()

    if not state_record:
        logger.warning(f"No ProjectState found for project {project_id}")
        return None

    raw_state = json.loads(state_record.state)
    raw_state = ensure_aaa_defaults(raw_state)
    try:
        state_data = AAAProjectState.model_validate(raw_state).model_dump(
            mode="json", exclude_none=True, by_alias=True
        )
    except ValidationError as exc:
        logger.warning(
            "ProjectState validation failed for %s; returning raw state (%s)",
            project_id,
            exc,
        )
        state_data = raw_state

    docs_result = await db.execute(
        select(ProjectDocument).where(ProjectDocument.project_id == project_id)
    )
    project_documents = docs_result.scalars().all()
    if project_documents:
        uploaded_reference_documents = [
            _document_to_reference_payload(document) for document in project_documents
        ]
        state_data["referenceDocuments"] = _merge_uploaded_reference_documents(
            state_data.get("referenceDocuments"),
            uploaded_reference_documents,
        )
        project_document_stats = _compute_project_document_stats(project_documents)
        state_data["projectDocumentStats"] = project_document_stats
        # Backward compatibility for older clients expecting ingestionStats.
        state_data["ingestionStats"] = project_document_stats

    state_data["projectId"] = project_id
    state_data["lastUpdated"] = state_record.updated_at

    # Phase 5: Dynamic WAF Reconstruction from Normalized DB
    # This ensures that even if the JSON state is out of sync, the frontend
    # sees the latest assessments from the checklists table.
    from app.core.app_settings import get_app_settings
    settings = get_app_settings()
    if settings.aaa_feature_waf_normalized:
        try:
            from contextlib import asynccontextmanager
            from pathlib import Path

            from ..checklists.engine import ChecklistEngine
            from ..checklists.registry import ChecklistRegistry

            @asynccontextmanager
            async def session_factory():
                yield db

            registry = ChecklistRegistry(Path(settings.waf_template_cache_dir), settings)
            engine = ChecklistEngine(session_factory, registry, settings)

            # Reconstruct wafChecklist
            reconstructed_waf = await engine.sync_db_to_project_state(project_id)

            # If DB only has a skeleton but JSON has real items, trigger a sync
            has_db_items = any(c.get("items") for c in reconstructed_waf.values())
            raw_waf = raw_state.get("wafChecklist", {})
            has_json_items = False
            if isinstance(raw_waf, dict):
                if raw_waf.get("items"): # Legacy flat format
                    has_json_items = True
                else: # Multi-template format
                    has_json_items = any(isinstance(v, dict) and v.get("items") for k, v in raw_waf.items() if k not in ["templates", "metadata"])

            if not has_db_items and has_json_items:
                logger.info(f"WAF data missing from DB for {project_id}, triggering sync from JSON")
                await engine.sync_project_state_to_db(project_id, raw_state)
                reconstructed_waf = await engine.sync_db_to_project_state(project_id)

            if reconstructed_waf:
                state_data["wafChecklist"] = _merge_reconstructed_waf_payloads(reconstructed_waf)

                # Also reconstruct findings if they are empty in the JSON but we have risks in DB
                if not state_data.get("findings"):
                    findings = []
                    # We might want a separate engine method for this,
                    # but for now let's derive them from the reconstructed checklist
                    items = state_data["wafChecklist"].get("items", [])
                    # Handle both list and dict formats for items (depending on engine fix)
                    if isinstance(items, dict):
                        item_values = items.values()
                    else:
                        item_values = items

                    for it in item_values:
                        # The reconstructed item has an evaluations list in the legacy format.
                        # We need to find the latest evaluation status.
                        evals = it.get("evaluations", [])
                        if not evals:
                            continue

                        latest_eval = evals[0] # normalize_helpers.py puts latest first
                        status = latest_eval.get("status")

                        # Legacy statuses that indicate a finding/issue
                        if status in ["partial", "notCovered", "at_risk", "failed"]:
                            findings.append({
                                "id": f"finding-{it.get('id') or it.get('title')}",
                                "title": it.get("title") or it.get("topic") or "WAF Issue",
                                "severity": it.get("severity", "medium"),
                                "description": latest_eval.get("evidence") or "Non-compliant WAF item detected.",
                                "remediation": "Review WAF best practices for this topic.",
                                "wafPillar": (it.get("pillar") or "General").lower().replace(" ", "")
                            })
                    if findings:
                        state_data["findings"] = findings
                        logger.debug(f"Derived {len(findings)} findings for project {project_id}")

                logger.debug(f"Reconstructed WAF checklist for project {project_id} from DB")
        except Exception as e:
            # Don't fail the whole request if reconstruction fails, just log it
            logger.error(f"Failed to reconstruct WAF for {project_id}: {e}", exc_info=True)

    logger.debug(f"Loaded ProjectState for project {project_id}")
    return state_data


async def update_project_state(
    project_id: str, updates: dict[str, Any], db: AsyncSession, merge: bool = True
) -> dict[str, Any]:
    """
    Update ProjectState in database.

    Args:
        project_id: Project ID
        updates: Dictionary with state updates
        db: Database session
        merge: If True, merge with existing state; if False, replace entirely

    Returns:
        Updated ProjectState dictionary

    Raises:
        ValueError: If project or state not found
    """
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise ValueError(f"Project {project_id} not found")

    # Get current state
    result = await db.execute(
        select(ProjectState).where(ProjectState.project_id == project_id)
    )
    state_record = result.scalar_one_or_none()

    if not state_record:
        raise ValueError(f"ProjectState not initialized for project {project_id}")

    # Merge or replace
    conflicts = []
    if merge:
        current_state = ensure_aaa_defaults(json.loads(state_record.state))
        merge_result = merge_state_updates_no_overwrite(current_state, updates)
        updated_state = ensure_aaa_defaults(merge_result.merged_state)
        conflicts = [c.__dict__ for c in merge_result.conflicts]
    else:
        updated_state = ensure_aaa_defaults(updates)

    # US6 enrichment: update mind map coverage and traceability without overwriting.
    if is_mindmap_initialized():
        updated_state = update_mindmap_coverage(updated_state)
    updated_state = apply_us6_enrichment(updated_state)

    # Validate/normalize through typed model to prevent corrupting persisted state
    try:
        validated = AAAProjectState.model_validate(updated_state)
        updated_state = validated.model_dump(mode="json", exclude_none=True, by_alias=True)
    except ValidationError as exc:
        raise ValueError(f"Invalid project state update payload: {exc}") from exc

    # Update database record
    state_record.state = json.dumps(updated_state)
    state_record.updated_at = datetime.now(timezone.utc).isoformat()

    # PHASE 5: Dual write to normalized WAF tables
    from app.core.app_settings import get_app_settings
    settings = get_app_settings()
    if settings.aaa_feature_waf_normalized:
        try:
            from contextlib import asynccontextmanager
            from pathlib import Path

            from ..checklists.engine import ChecklistEngine
            from ..checklists.registry import ChecklistRegistry

            @asynccontextmanager
            async def session_factory():
                yield db

            registry = ChecklistRegistry(Path(settings.waf_template_cache_dir), settings)
            engine = ChecklistEngine(session_factory, registry, settings)
            await engine.sync_project_state_to_db(project_id, updated_state)
            logger.info(f"Sync'd project state to normalized WAF tables for {project_id}")
        except Exception as e:
            logger.error(f"Failed to sync WAF state to DB for {project_id}: {e}", exc_info=True)

    # Don't commit here - let the dependency handle it
    await db.flush()  # Flush to get updated values but don't commit

    # Return with metadata
    response_state = dict(updated_state)
    response_state["projectId"] = project_id
    response_state["lastUpdated"] = state_record.updated_at
    if conflicts:
        response_state["conflicts"] = conflicts

    logger.info(f"Updated ProjectState for project {project_id}")
    return response_state


def _deep_merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Deprecated: retained for compatibility, prefer merge_state_updates_no_overwrite."""
    result = base.copy()
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _merge_reconstructed_waf_payloads(reconstructed: dict[str, Any]) -> dict[str, Any]:
    """Merge multi-template reconstructed WAF payload into legacy checklist shape."""
    all_items: list[dict[str, Any]] = []
    pillar_order: list[str] = []
    seen_pillars: set[str] = set()
    versions: set[str] = set()

    for payload in reconstructed.values():
        if not isinstance(payload, dict):
            continue

        version = payload.get("version")
        if isinstance(version, str) and version.strip():
            versions.add(version.strip())

        pillars = payload.get("pillars")
        if isinstance(pillars, list):
            for pillar in pillars:
                name = str(pillar).strip()
                if not name or name in seen_pillars:
                    continue
                seen_pillars.add(name)
                pillar_order.append(name)

        items = payload.get("items")
        if isinstance(items, list):
            all_items.extend(item for item in items if isinstance(item, dict))
        elif isinstance(items, dict):
            all_items.extend(item for item in items.values() if isinstance(item, dict))

    version = versions.pop() if len(versions) == 1 else "multi"
    return {"version": version, "pillars": pillar_order, "items": all_items}


async def get_project_context_summary(project_id: str, db: AsyncSession) -> str:
    """
    Get formatted summary of project context for agent prompts.

    Args:
        project_id: Project ID
        db: Database session

    Returns:
        Formatted string with project context
    """
    # Get project info
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        return f"Project {project_id} not found"

    # Get state
    state = await read_project_state(project_id, db)
    if not state:
        return f"PROJECT: {project.name}\nNo architecture state available yet."

    summary_parts = [f"PROJECT: {project.name}", f"Created: {project.created_at}", ""]

    _add_project_context_section(summary_parts, state)
    _add_nfr_section(summary_parts, state)
    _add_application_structure_section(summary_parts, state)
    _add_open_questions_section(summary_parts, state)

    return "\n".join(summary_parts).strip()


def _add_project_context_section(parts: list[str], state: dict[str, Any]) -> None:
    """Add general context fields to summary."""
    ctx = state.get("context")
    if not ctx:
        return

    parts.append("CONTEXT:")
    if ctx.get("summary"):
        parts.append(f"  Summary: {ctx['summary']}")
    if ctx.get("objectives"):
        parts.append(f"  Objectives: {', '.join(ctx['objectives'])}")
    if ctx.get("targetUsers"):
        parts.append(f"  Target Users: {ctx['targetUsers']}")
    if ctx.get("scenarioType"):
        parts.append(f"  Scenario: {ctx['scenarioType']}")
    parts.append("")


def _add_nfr_section(parts: list[str], state: dict[str, Any]) -> None:
    """Add Non-Functional Requirements to summary."""
    nfrs = state.get("nfrs")
    if not nfrs:
        return

    parts.append("NON-FUNCTIONAL REQUIREMENTS:")
    if nfrs.get("availability"):
        parts.append(f"  Availability: {nfrs['availability']}")
    if nfrs.get("security"):
        parts.append(f"  Security: {nfrs['security']}")
    if nfrs.get("performance"):
        parts.append(f"  Performance: {nfrs['performance']}")
    if nfrs.get("costConstraints"):
        parts.append(f"  Cost: {nfrs['costConstraints']}")
    parts.append("")


def _add_application_structure_section(parts: list[str], state: dict[str, Any]) -> None:
    """Add components and integrations to summary."""
    app_struct = state.get("applicationStructure")
    if not app_struct:
        return

    parts.append("APPLICATION STRUCTURE:")
    components = app_struct.get("components", [])
    if components:
        parts.append(f"  Components: {len(components)} defined")
        for comp in components[:3]:  # Show first 3
            parts.append(
                f"    - {comp.get('name', 'Unnamed')}: {comp.get('description', '')[:50]}"
            )

    integrations = app_struct.get("integrations", [])
    if integrations:
        parts.append(f"  Integrations: {', '.join(integrations[:5])}")
    parts.append("")


def _add_open_questions_section(parts: list[str], state: dict[str, Any]) -> None:
    """Add high-priority open questions to summary."""
    questions = state.get("openQuestions", [])
    if not questions:
        return

    parts.append("OPEN QUESTIONS:")
    for q in questions[:5]:
        parts.append(f"  - {q}")
    parts.append("")

