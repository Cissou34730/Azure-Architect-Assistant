import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, ProjectDocument, ProjectState
from app.services import llm_service

from .document_parsing import extract_text_from_upload

logger = logging.getLogger(__name__)


class DocumentService:
    """Handles document upload and analysis for projects."""

    async def upload_documents(
        self,
        project_id: str,
        files: list[Any],
        db: AsyncSession,
    ) -> list[dict[str, Any]]:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        saved_docs: list[ProjectDocument] = []
        attempted_documents = 0
        parsed_documents = 0
        failures: list[dict[str, Any]] = []

        for file in files:
            attempted_documents += 1
            content = await file.read()

            extracted_text, failure_reason = extract_text_from_upload(
                file_name=file.filename,
                mime_type=getattr(file, "content_type", None),
                content=content,
            )

            if extracted_text is None:
                failures.append(
                    {
                        "documentId": None,
                        "fileName": file.filename,
                        "reason": failure_reason or "unknown parse failure",
                    }
                )
                extracted_text = ""  # Persist empty text but keep the document record
            else:
                parsed_documents += 1

            doc = ProjectDocument(
                id=str(uuid.uuid4()),
                project_id=project_id,
                file_name=file.filename,
                mime_type=getattr(file, "content_type", "application/octet-stream"),
                raw_text=extracted_text,
                uploaded_at=datetime.now(timezone.utc).isoformat(),
            )

            db.add(doc)
            saved_docs.append(doc)

        await db.commit()

        # Persist ingestion stats into ProjectState (SC-004) without blocking upload.
        try:
            stats_payload = {
                "projectDocumentStats": {
                    "attemptedDocuments": attempted_documents,
                    "parsedDocuments": parsed_documents,
                    "failedDocuments": max(attempted_documents - parsed_documents, 0),
                    "failures": failures,
                }
            }

            state_result = await db.execute(
                select(ProjectState).where(ProjectState.project_id == project_id)
            )
            state_record = state_result.scalar_one_or_none()

            if state_record:
                current_state = json.loads(state_record.state)
                current_state.update(stats_payload)
                state_record.state = json.dumps(current_state)
                state_record.updated_at = datetime.now(timezone.utc).isoformat()
            else:
                db.add(
                    ProjectState(
                        project_id=project_id,
                        state=json.dumps(stats_payload),
                        updated_at=datetime.now(timezone.utc).isoformat(),
                    )
                )

            await db.commit()
        except Exception:
            logger.exception(
                "Failed to persist projectDocumentStats for project %s",
                project_id,
            )

        logger.info(f"Uploaded {len(saved_docs)} documents for project: {project_id}")
        return [doc.to_dict() for doc in saved_docs]

    def _prepare_document_texts(
        self, project: Project, documents: list[ProjectDocument]
    ) -> list[str]:
        """Combine project text requirements and uploaded document contents for LLM."""
        texts = [
            f"DocumentId: {doc.id}\nFileName: {doc.file_name}\n---\n{doc.raw_text}"
            for doc in documents
            if (doc.raw_text or "").strip()
        ]
        if project.text_requirements:
            texts.append(project.text_requirements)
        return texts

    def _compute_ingestion_stats(
        self, documents: list[ProjectDocument]
    ) -> dict[str, Any]:
        """Calculate document processing success and failure metrics."""
        parsed = 0
        failures = []
        for doc in documents:
            if (doc.raw_text or "").strip():
                parsed += 1
            else:
                failures.append(
                    {
                        "documentId": doc.id,
                        "fileName": doc.file_name,
                        "reason": "no extractable text",
                    }
                )

        return {
            "attemptedDocuments": len(documents),
            "parsedDocuments": parsed,
            "failedDocuments": max(len(documents) - parsed, 0),
            "failures": failures,
        }

    async def analyze_documents(
        self, project_id: str, db: AsyncSession
    ) -> dict[str, Any]:
        """Run AI analysis on documents and persist project state."""
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        result = await db.execute(
            select(ProjectDocument).where(ProjectDocument.project_id == project_id)
        )
        documents = result.scalars().all()

        texts = self._prepare_document_texts(project, documents)
        if not texts:
            raise ValueError("No content to analyze (missing text and documents)")

        logger.info(f"Analyzing {len(texts)} content blocks for project: {project_id}")

        service = llm_service.get_llm_service()
        state_data = await service.analyze_documents(texts)

        _normalize_aaa_requirements_and_questions(state_data)

        # Append telemetry/stats (SC-004)
        state_data["projectDocumentStats"] = self._compute_ingestion_stats(documents)

        state_json = json.dumps(state_data)
        result = await db.execute(
            select(ProjectState).where(ProjectState.project_id == project_id)
        )
        existing_state = result.scalar_one_or_none()

        if existing_state:
            existing_state.state = state_json
            existing_state.updated_at = datetime.now(timezone.utc).isoformat()
        else:
            new_state = ProjectState(
                project_id=project_id,
                state=state_json,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            db.add(new_state)

        await db.commit()
        logger.info(f"Document analysis completed for project: {project_id}")
        return cast(dict[str, Any], state_data)

    async def generate_proposal(
        self,
        project_id: str,
        db: AsyncSession,
        on_progress: Any | None = None,
    ) -> str:
        """Generate architecture proposal for a project."""
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        result = await db.execute(
            select(ProjectState).where(ProjectState.project_id == project_id)
        )
        state_record = result.scalar_one_or_none()
        if not state_record:
            raise ValueError(
            )

        state = json.loads(state_record.state)

        llm_service = get_llm_service()
        proposal = await llm_service.generate_architecture_proposal(state, on_progress)
        return cast(str, proposal)


def _normalize_aaa_requirements_and_questions(state_data: dict[str, Any]) -> None:
    """Ensure AAA requirements/questions exist and have stable IDs.

    This keeps the state aligned to the AAA data model (specs/002-azure-architect-assistant/data-model.md)
    without relying on the LLM to generate UUIDs.
    """
    _normalize_requirements(state_data)
    _normalize_questions(state_data)


def _normalize_requirements(state_data: dict[str, Any]) -> None:
    """Normalize requirements list."""
    requirements: list[dict[str, Any]] = []
    raw_requirements = state_data.get("requirements", []) or []

    for item in raw_requirements:
        normalized = _normalize_single_requirement(item)
        if normalized:
            requirements.append(normalized)

    # Preserve existing requirements if already present
    if not state_data.get("requirements"):
        state_data["requirements"] = requirements
    else:
        existing_reqs = state_data.get("requirements", [])
        if isinstance(existing_reqs, list):
            for r in existing_reqs:
                if isinstance(r, dict) and not r.get("id"):
                    r["id"] = str(uuid.uuid4())


def _extract_category(item: dict[str, Any]) -> str:
    """Extract and normalize requirement category."""
    category = (item.get("category") or "").strip().lower()
    return category if category in {"business", "functional", "nfr"} else "functional"


def _extract_ambiguity(item: dict[str, Any]) -> dict[str, Any]:
    """Extract and normalize requirement ambiguity info."""
    ambiguity_raw = item.get("ambiguity")
    ambiguity = ambiguity_raw if isinstance(ambiguity_raw, dict) else {}
    is_ambiguous = bool(ambiguity.get("isAmbiguous", False))
    notes = (ambiguity.get("notes") or "").strip()

    if is_ambiguous or notes:
        return {"isAmbiguous": is_ambiguous, "notes": notes}
    return {"isAmbiguous": False}


def _extract_sources(item: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract and normalize requirement sources."""
    sources_raw = item.get("sources")
    sources = sources_raw if isinstance(sources_raw, list) else []
    normalized_sources: list[dict[str, Any]] = []

    for s in sources:
        if isinstance(s, dict):
            normalized_sources.append(
                {
                    "documentId": s.get("documentId"),
                    "fileName": s.get("fileName"),
                    "excerpt": s.get("excerpt"),
                }
            )
    return normalized_sources


def _normalize_single_requirement(item: Any) -> dict[str, Any] | None:
    """Normalize a single requirement item."""
    if not isinstance(item, dict):
        return None

    text = (item.get("text") or "").strip()
    if not text:
        return None

    return {
        "id": item.get("id") or str(uuid.uuid4()),
        "category": _extract_category(item),
        "text": text,
        "ambiguity": _extract_ambiguity(item),
        "sources": _extract_sources(item),
    }


def _normalize_questions(state_data: dict[str, Any]) -> None:
    """Normalize clarification questions and handle linking."""
    req_list: list[dict[str, Any]] = state_data.get("requirements") or []
    req_ids_by_index: dict[int, str] = {
        idx: r["id"]
        for idx, r in enumerate(req_list)
        if isinstance(r, dict) and isinstance(r.get("id"), str)
    }

    clarification_questions: list[dict[str, Any]] = []
    raw_questions = state_data.get("clarificationQuestions", []) or []

    for q in raw_questions:
        normalized = _normalize_single_question(q, req_ids_by_index)
        if normalized:
            clarification_questions.append(normalized)

    # Fallback to openQuestions list (legacy field)
    if not clarification_questions:
        clarification_questions = _get_clarification_questions_from_legacy(state_data)

    if not state_data.get("clarificationQuestions"):
        state_data["clarificationQuestions"] = clarification_questions
    else:
        _ensure_ids_on_existing_questions(state_data)


def _normalize_single_question(
    q: Any, req_ids_by_index: dict[int, str]
) -> dict[str, Any] | None:
    """Normalize a single clarification question."""
    if not isinstance(q, dict):
        return None

    question_text = (q.get("question") or "").strip()
    if not question_text:
        return None

    related_indexes = q.get("relatedRequirementIndexes")
    related_requirement_ids: list[str] = []
    if isinstance(related_indexes, list):
        for idx in related_indexes:
            if isinstance(idx, int) and idx in req_ids_by_index:
                related_requirement_ids.append(req_ids_by_index[idx])

    return {
        "id": q.get("id") or str(uuid.uuid4()),
        "question": question_text,
        "status": q.get("status") or "open",
        "priority": q.get("priority"),
        "relatedRequirementIds": related_requirement_ids,
    }


def _get_clarification_questions_from_legacy(
    state_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Fallback to openQuestions list (legacy field)."""
    clarification_questions: list[dict[str, Any]] = []
    for oq in state_data.get("openQuestions", []) or []:
        if isinstance(oq, str) and oq.strip():
            clarification_questions.append(
                {
                    "id": str(uuid.uuid4()),
                    "question": oq.strip(),
                    "status": "open",
                    "relatedRequirementIds": [],
                }
            )
    return clarification_questions


def _ensure_ids_on_existing_questions(state_data: dict[str, Any]) -> None:
    """Ensure ids exist for any existing items."""
    existing_qs = state_data.get("clarificationQuestions", [])
    if isinstance(existing_qs, list):
        for qq in existing_qs:
            if isinstance(qq, dict) and not qq.get("id"):
                qq["id"] = str(uuid.uuid4())

