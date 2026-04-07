import logging
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.services.aaa_state_models import ensure_aaa_defaults
from app.agents_system.services.project_context import read_project_state
from app.features.projects.infrastructure.project_state_decomposition import (
    compose_project_state,
)
from app.features.projects.infrastructure.project_state_store import ProjectStateStore
from app.models import Project, ProjectDocument
from app.shared.ai import llm_service
from app.shared.config.app_settings import get_app_settings

from .document_normalization import (
    normalize_aaa_requirements_and_questions,
)
from .document_parsing import extract_text_from_upload

logger = logging.getLogger(__name__)
_project_state_store = ProjectStateStore()


PARSE_STATUS_PARSED = "parsed"
PARSE_STATUS_FAILED = "parse_failed"
ANALYSIS_STATUS_NOT_STARTED = "not_started"
ANALYSIS_STATUS_ANALYZING = "analyzing"
ANALYSIS_STATUS_ANALYZED = "analyzed"
ANALYSIS_STATUS_FAILED = "analysis_failed"
ANALYSIS_STATUS_SKIPPED = "skipped"


class DocumentService:
    """Handles document upload and analysis for projects."""

    def __init__(self) -> None:
        document_store_dir = get_app_settings().project_documents_root
        if document_store_dir is None:
            raise ValueError("PROJECT_DOCUMENTS_ROOT must be configured")
        self.document_store_dir = document_store_dir

    async def upload_documents(  # noqa: PLR0915
        self,
        project_id: str,
        files: list[Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
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
            document_id = str(uuid.uuid4())
            safe_file_name = Path(file.filename or "document").name
            uploaded_mime_type = (getattr(file, "content_type", None) or "").strip()
            if uploaded_mime_type in {"", "application/octet-stream"}:
                guessed_mime_type, _ = mimetypes.guess_type(safe_file_name)
                if guessed_mime_type:
                    uploaded_mime_type = guessed_mime_type
            if uploaded_mime_type == "":
                uploaded_mime_type = "application/octet-stream"
            storage_dir = self.document_store_dir / project_id
            storage_dir.mkdir(parents=True, exist_ok=True)
            stored_path = storage_dir / f"{document_id}_{safe_file_name}"
            stored_path.write_bytes(content)

            extracted_text, failure_reason = extract_text_from_upload(
                file_name=safe_file_name,
                mime_type=uploaded_mime_type,
                content=content,
            )

            if extracted_text is None:
                parse_status = PARSE_STATUS_FAILED
                parse_error = failure_reason or "unknown parse failure"
                analysis_status = ANALYSIS_STATUS_SKIPPED
                failures.append(
                    {
                        "documentId": document_id,
                        "fileName": file.filename,
                        "reason": parse_error,
                    }
                )
                extracted_text = ""  # Persist empty text but keep the document record
            else:
                parse_status = PARSE_STATUS_PARSED
                parse_error = None
                analysis_status = ANALYSIS_STATUS_NOT_STARTED
                parsed_documents += 1

            doc = ProjectDocument(
                id=document_id,
                project_id=project_id,
                file_name=safe_file_name,
                mime_type=uploaded_mime_type,
                raw_text=extracted_text,
                stored_path=str(stored_path),
                parse_status=parse_status,
                analysis_status=analysis_status,
                parse_error=parse_error,
                uploaded_at=datetime.now(timezone.utc).isoformat(),
            )

            db.add(doc)
            saved_docs.append(doc)

        await db.commit()

        upload_summary = {
            "attemptedDocuments": attempted_documents,
            "parsedDocuments": parsed_documents,
            "failedDocuments": max(attempted_documents - parsed_documents, 0),
            "failures": failures,
        }

        # Persist document stats + reference docs into ProjectState without blocking upload.
        try:
            all_documents = await self._fetch_project_documents(project_id, db)
            computed_stats = self._compute_ingestion_stats(all_documents)
            reference_documents = self._build_reference_documents(all_documents)

            blob_state = await _project_state_store.get_blob_state(project_id=project_id, db=db)

            if blob_state is not None:
                current_state = await compose_project_state(
                    project_id=project_id,
                    state=blob_state,
                    db=db,
                )
                merged_reference_documents = self._merge_reference_documents(
                    current_state.get("referenceDocuments"),
                    reference_documents,
                )
                current_state["projectDocumentStats"] = computed_stats
                # Backward compatibility for existing consumers/tests.
                current_state["ingestionStats"] = computed_stats
                current_state["referenceDocuments"] = merged_reference_documents
                current_state = ensure_aaa_defaults(current_state)
                updated_at = datetime.now(timezone.utc).isoformat()
                await _project_state_store.persist_composed_state(
                    project_id=project_id,
                    state=current_state,
                    db=db,
                    replace_missing=False,
                    updated_at=updated_at,
                )
            else:
                seed_state = ensure_aaa_defaults({})
                seed_state["projectDocumentStats"] = computed_stats
                seed_state["ingestionStats"] = computed_stats
                seed_state["referenceDocuments"] = reference_documents
                updated_at = datetime.now(timezone.utc).isoformat()
                await _project_state_store.persist_composed_state(
                    project_id=project_id,
                    state=seed_state,
                    db=db,
                    replace_missing=False,
                    updated_at=updated_at,
                )

            await db.commit()
        except Exception:
            logger.exception(
                "Failed to persist projectDocumentStats/referenceDocuments for project %s",
                project_id,
            )

        logger.info(f"Uploaded {len(saved_docs)} documents for project: {project_id}")
        return {
            "documents": [doc.to_dict() for doc in saved_docs],
            "uploadSummary": upload_summary,
        }

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
            parse_status = (
                doc.parse_status
                if doc.parse_status is not None
                else PARSE_STATUS_PARSED if (doc.raw_text or "").strip() else PARSE_STATUS_FAILED
            )
            if parse_status == PARSE_STATUS_PARSED:
                parsed += 1
            else:
                failures.append(
                    {
                        "documentId": doc.id,
                        "fileName": doc.file_name,
                        "reason": doc.parse_error or "no extractable text",
                    }
                )

        return {
            "attemptedDocuments": len(documents),
            "parsedDocuments": parsed,
            "failedDocuments": max(len(documents) - parsed, 0),
            "failures": failures,
        }

    async def _fetch_project_documents(
        self, project_id: str, db: AsyncSession
    ) -> list[ProjectDocument]:
        result = await db.execute(
            select(ProjectDocument).where(ProjectDocument.project_id == project_id)
        )
        return list(result.scalars().all())

    def _build_reference_documents(
        self, documents: list[ProjectDocument]
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": doc.id,
                "category": "uploaded",
                "title": doc.file_name,
                "url": f"/api/projects/{doc.project_id}/documents/{doc.id}/content"
                if doc.stored_path
                else None,
                "mimeType": doc.mime_type,
                "accessedAt": doc.uploaded_at,
                "parseStatus": doc.parse_status
                or (
                    PARSE_STATUS_PARSED
                    if (doc.raw_text or "").strip()
                    else PARSE_STATUS_FAILED
                ),
                "analysisStatus": doc.analysis_status
                or (
                    ANALYSIS_STATUS_NOT_STARTED
                    if (doc.raw_text or "").strip()
                    else ANALYSIS_STATUS_SKIPPED
                ),
                "parseError": doc.parse_error,
                "uploadedAt": doc.uploaded_at,
                "analyzedAt": doc.analyzed_at,
            }
            for doc in documents
        ]

    def _merge_reference_documents(
        self,
        current_reference_documents: Any,
        uploaded_reference_documents: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged_by_id: dict[str, dict[str, Any]] = {}
        if isinstance(current_reference_documents, list):
            for item in current_reference_documents:
                if isinstance(item, dict):
                    item_id = str(item.get("id") or "").strip()
                    if item_id != "":
                        merged_by_id[item_id] = dict(item)

        for uploaded_doc in uploaded_reference_documents:
            merged_by_id[uploaded_doc["id"]] = uploaded_doc

        return list(merged_by_id.values())

    def _apply_analysis_status_start(
        self, documents: list[ProjectDocument], run_id: str
    ) -> None:
        for doc in documents:
            parse_status = doc.parse_status or (
                PARSE_STATUS_PARSED
                if (doc.raw_text or "").strip()
                else PARSE_STATUS_FAILED
            )
            doc.last_analysis_run_id = run_id
            if parse_status == PARSE_STATUS_PARSED:
                doc.analysis_status = ANALYSIS_STATUS_ANALYZING
            else:
                doc.analysis_status = ANALYSIS_STATUS_SKIPPED

    def _apply_analysis_status_success(
        self, documents: list[ProjectDocument], run_id: str, completed_at: str
    ) -> tuple[int, int]:
        analyzed_documents = 0
        skipped_documents = 0
        for doc in documents:
            parse_status = doc.parse_status or (
                PARSE_STATUS_PARSED
                if (doc.raw_text or "").strip()
                else PARSE_STATUS_FAILED
            )
            doc.last_analysis_run_id = run_id
            if parse_status == PARSE_STATUS_PARSED:
                analyzed_documents += 1
                doc.analysis_status = ANALYSIS_STATUS_ANALYZED
                doc.analyzed_at = completed_at
            else:
                skipped_documents += 1
                doc.analysis_status = ANALYSIS_STATUS_SKIPPED
        return analyzed_documents, skipped_documents

    def _apply_analysis_status_failed(
        self, documents: list[ProjectDocument], run_id: str
    ) -> None:
        for doc in documents:
            parse_status = doc.parse_status or (
                PARSE_STATUS_PARSED
                if (doc.raw_text or "").strip()
                else PARSE_STATUS_FAILED
            )
            doc.last_analysis_run_id = run_id
            if parse_status == PARSE_STATUS_PARSED:
                doc.analysis_status = ANALYSIS_STATUS_FAILED

    async def analyze_documents(
        self, project_id: str, db: AsyncSession
    ) -> dict[str, Any]:
        """Run AI analysis on documents and persist project state."""
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        documents = await self._fetch_project_documents(project_id, db)
        analysis_run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()
        self._apply_analysis_status_start(documents, analysis_run_id)
        await db.flush()

        texts = self._prepare_document_texts(project, documents)
        if not texts:
            raise ValueError("No content to analyze (missing text and documents)")

        logger.info(f"Analyzing {len(texts)} content blocks for project: {project_id}")

        service = llm_service.get_llm_service()
        try:
            state_data = await service.analyze_documents(texts)
        except Exception:
            self._apply_analysis_status_failed(documents, analysis_run_id)
            await db.commit()
            raise

        normalize_aaa_requirements_and_questions(state_data)
        completed_at = datetime.now(timezone.utc).isoformat()
        analyzed_documents, skipped_documents = self._apply_analysis_status_success(
            documents,
            analysis_run_id,
            completed_at,
        )

        # Append telemetry/stats and setup summary.
        stats = self._compute_ingestion_stats(documents)
        state_data["projectDocumentStats"] = stats
        # Backward compatibility for existing consumers/tests.
        state_data["ingestionStats"] = stats
        state_data["analysisSummary"] = {
            "runId": analysis_run_id,
            "startedAt": started_at,
            "completedAt": completed_at,
            "status": "success",
            "analyzedDocuments": analyzed_documents,
            "skippedDocuments": skipped_documents,
        }
        state_data["referenceDocuments"] = self._merge_reference_documents(
            state_data.get("referenceDocuments"),
            self._build_reference_documents(documents),
        )

        # Ensure AAA default keys exist even if the LLM omitted them.
        state_data = ensure_aaa_defaults(state_data)

        updated_at = datetime.now(timezone.utc).isoformat()
        await _project_state_store.persist_composed_state(
            project_id=project_id,
            state=state_data,
            db=db,
            replace_missing=True,
            updated_at=updated_at,
        )

        await db.commit()
        logger.info(f"✓ ProjectState persisted to DB: project_id={project_id}")
        return state_data

        # Unreachable: return above.

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

        state = await read_project_state(project_id, db)
        if not state:
            raise ValueError(
                "Project state not initialized. Please analyze documents first."
            )

        service = llm_service.get_llm_service()
        proposal = await service.generate_architecture_proposal(state, on_progress)
        return cast(str, proposal)

