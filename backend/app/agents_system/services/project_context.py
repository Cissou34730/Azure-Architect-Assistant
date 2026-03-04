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


async def read_project_state(project_id: str, db: AsyncSession) -> dict[str, Any] | None:
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

    sanitized_updates = dict(updates)
    sanitized_updates.pop("wafChecklist", None)

    # Merge or replace
    conflicts = []
    if merge:
        current_state = ensure_aaa_defaults(json.loads(state_record.state))
        current_state.pop("wafChecklist", None)
        merge_result = merge_state_updates_no_overwrite(current_state, sanitized_updates)
        updated_state = ensure_aaa_defaults(merge_result.merged_state)
        conflicts = [c.__dict__ for c in merge_result.conflicts]
    else:
        updated_state = ensure_aaa_defaults(sanitized_updates)

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


async def get_project_context_summary(project_id: str, db: AsyncSession) -> str:
    """
    Get formatted summary of project context for agent prompts.

    Includes: context, NFRs, requirements, technical constraints, data compliance,
    application structure, open questions, clarification questions, and document excerpts.

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

    # Load uploaded document texts for excerpt inclusion
    docs_result = await db.execute(
        select(ProjectDocument).where(ProjectDocument.project_id == project_id)
    )
    project_documents = docs_result.scalars().all()
    documents_text: dict[str, str] = {}
    for doc in project_documents:
        if (doc.raw_text or "").strip() and doc.parse_status == "parsed":
            documents_text[doc.id] = doc.raw_text

    summary_parts = [f"PROJECT: {project.name}", f"Created: {project.created_at}", ""]

    _add_project_context_section(summary_parts, state)
    _add_nfr_section(summary_parts, state)
    _add_requirements_section(summary_parts, state)
    _add_technical_constraints_section(summary_parts, state)
    _add_data_compliance_section(summary_parts, state)
    _add_application_structure_section(summary_parts, state)
    _add_open_questions_section(summary_parts, state)
    _add_clarification_questions_section(summary_parts, state)
    _add_document_excerpts_section(summary_parts, state, documents_text)

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


# Maximum characters per document excerpt included in context summary
_DOCUMENT_EXCERPT_MAX_CHARS = 2000


def _add_requirements_section(parts: list[str], state: dict[str, Any]) -> None:  # noqa: C901
    """Add extracted requirements with category, ambiguity, and sources to summary."""
    requirements = state.get("requirements")
    if not requirements:
        return

    parts.append("REQUIREMENTS:")
    for req in requirements:
        if not isinstance(req, dict):
            continue
        category = req.get("category", "unknown")
        text = req.get("text", "")
        if not text:
            continue

        line = f"  [{category}] {text}"

        ambiguity = req.get("ambiguity")
        if isinstance(ambiguity, dict) and ambiguity.get("isAmbiguous"):
            notes = ambiguity.get("notes", "")
            line += f" [AMBIGUOUS: {notes}]" if notes else " [AMBIGUOUS]"

        parts.append(line)

        sources = req.get("sources")
        if isinstance(sources, list):
            for src in sources:
                if isinstance(src, dict):
                    file_name = src.get("fileName", "")
                    excerpt = src.get("excerpt", "")
                    if file_name:
                        src_line = f"    Source: {file_name}"
                        if excerpt:
                            src_line += f" — \"{excerpt}\""
                        parts.append(src_line)

    parts.append("")


def _add_technical_constraints_section(
    parts: list[str], state: dict[str, Any]
) -> None:
    """Add technical constraints and assumptions to summary."""
    tc = state.get("technicalConstraints")
    if not tc:
        return

    constraints = tc.get("constraints", [])
    assumptions = tc.get("assumptions", [])
    if not constraints and not assumptions:
        return

    parts.append("TECHNICAL CONSTRAINTS:")
    for c in constraints:
        parts.append(f"  - {c}")

    if assumptions:
        parts.append("  Assumptions:")
        for a in assumptions:
            parts.append(f"    - {a}")
    parts.append("")


def _add_data_compliance_section(parts: list[str], state: dict[str, Any]) -> None:
    """Add data compliance, data types, and residency to summary."""
    dc = state.get("dataCompliance")
    if not dc:
        return

    data_types = dc.get("dataTypes", [])
    compliance_reqs = dc.get("complianceRequirements", [])
    residency = dc.get("dataResidency")
    if not data_types and not compliance_reqs and not residency:
        return

    parts.append("DATA COMPLIANCE:")
    if data_types:
        parts.append(f"  Data Types: {', '.join(str(d) for d in data_types)}")
    if compliance_reqs:
        parts.append(f"  Compliance: {', '.join(str(r) for r in compliance_reqs)}")
    if residency:
        parts.append(f"  Data Residency: {residency}")
    parts.append("")


def _add_clarification_questions_section(
    parts: list[str], state: dict[str, Any]
) -> None:
    """Add clarification questions from the analysis to summary."""
    questions = state.get("clarificationQuestions")
    if not questions:
        return

    parts.append("CLARIFICATION QUESTIONS:")
    for q in questions:
        if isinstance(q, dict):
            text = q.get("question", "")
            priority = q.get("priority")
            if text:
                prefix = f"  [P{priority}]" if priority else "  -"
                parts.append(f"{prefix} {text}")
        elif isinstance(q, str):
            parts.append(f"  - {q}")
    parts.append("")


def _add_document_excerpts_section(
    parts: list[str],
    state: dict[str, Any],
    documents_text: dict[str, str],
) -> None:
    """Add excerpts from uploaded project documents to summary."""
    ref_docs = state.get("referenceDocuments")
    if not ref_docs or not documents_text:
        return

    uploaded = [
        d
        for d in ref_docs
        if isinstance(d, dict)
        and d.get("category") == "uploaded"
        and d.get("parseStatus") == "parsed"
    ]
    if not uploaded:
        return

    parts.append("UPLOADED DOCUMENTS:")
    for doc_ref in uploaded:
        doc_id = doc_ref.get("id", "")
        title = doc_ref.get("title", "Unknown")
        text = documents_text.get(doc_id, "")
        if not text:
            parts.append(f"  [{title}] (no text available)")
            continue

        excerpt = text[:_DOCUMENT_EXCERPT_MAX_CHARS]
        if len(text) > _DOCUMENT_EXCERPT_MAX_CHARS:
            excerpt += "..."
        parts.append(f"  [{title}]")
        parts.append(f"    {excerpt}")
    parts.append("")

