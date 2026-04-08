"""Worker helpers for the first extract-requirements slice."""

from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Protocol

from app.features.agent.application.requirements_extraction_service import (
    RequirementsExtractionService,
)
from app.features.agent.contracts import ExtractedRequirementContract
from app.features.projects.application.document_normalization import (
    normalize_aaa_requirements_and_questions,
)
from app.features.projects.contracts import (
    ArtifactDraftType,
    ChangeSetStatus,
    PendingChangeSetContract,
)
from app.shared.ai import llm_service


class PendingChangeRecorder(Protocol):
    async def record_pending_change(
        self,
        *,
        project_id: str,
        change_set: PendingChangeSetContract,
        db: object,
    ) -> PendingChangeSetContract: ...


class RequirementsExtractionWorker:
    """Extract requirements from parsed documents and record a pending bundle."""

    def __init__(
        self,
        *,
        analyzer: Callable[[list[str]], Awaitable[dict[str, Any]] | dict[str, Any]] | None = None,
        pending_change_recorder: PendingChangeRecorder,
        extraction_service: RequirementsExtractionService | None = None,
    ) -> None:
        self._analyzer = analyzer or llm_service.get_llm_service().analyze_documents
        self._pending_change_recorder = pending_change_recorder
        self._extraction_service = extraction_service or RequirementsExtractionService()

    async def extract_and_record_requirements(
        self,
        *,
        project_id: str,
        document_payloads: list[dict[str, Any]],
        db: object,
        source_message_id: str | None = None,
    ) -> PendingChangeSetContract:
        formatted_documents = self._format_document_payloads(document_payloads)
        if not formatted_documents:
            raise ValueError("No parsed documents available for extraction")

        analysis = await self._run_analyzer(formatted_documents)
        normalize_aaa_requirements_and_questions(analysis)
        extracted_requirements = [
            ExtractedRequirementContract.model_validate(
                self._sanitize_requirement_payload(requirement)
            )
            for requirement in analysis.get("requirements", [])
            if isinstance(requirement, dict)
        ]

        assumptions = self._extract_assumptions(analysis)
        extraction_result = self._extraction_service.build_result(
            requirements=extracted_requirements,
            assumptions=assumptions,
            chunks_processed=len(formatted_documents),
        )
        change_set = self._build_change_set(
            project_id=project_id,
            source_message_id=source_message_id,
            extraction_result=extraction_result,
            document_count=len(formatted_documents),
        )
        return await self._pending_change_recorder.record_pending_change(
            project_id=project_id,
            change_set=change_set,
            db=db,
        )

    async def _run_analyzer(self, document_payloads: list[str]) -> dict[str, Any]:
        result = self._analyzer(document_payloads)
        if inspect.isawaitable(result):
            result = await result
        if not isinstance(result, dict):
            raise ValueError("Requirements analyzer returned an invalid payload")
        return result

    def _format_document_payloads(self, document_payloads: list[dict[str, Any]]) -> list[str]:
        formatted: list[str] = []
        for document in document_payloads:
            raw_text = str(document.get("rawText") or "").strip()
            if not raw_text:
                continue
            formatted.append(
                "\n".join(
                    [
                        f"DocumentId: {document.get('id')}",
                        f"FileName: {document.get('fileName')}",
                        raw_text,
                    ]
                )
            )
        return formatted

    def _sanitize_requirement_payload(self, requirement: dict[str, Any]) -> dict[str, Any]:
        sources = requirement.get("sources", [])
        sanitized_sources: list[dict[str, Any]] = []
        if isinstance(sources, list):
            for source in sources:
                if not isinstance(source, dict):
                    continue
                sanitized_sources.append(
                    {
                        "documentId": source.get("documentId"),
                        "excerpt": source.get("excerpt"),
                        "location": source.get("location"),
                    }
                )

        return {
            "text": requirement.get("text", ""),
            "category": requirement.get("category", "functional"),
            "ambiguity": requirement.get("ambiguity", {"isAmbiguous": False, "notes": ""}),
            "sources": sanitized_sources,
        }

    def _extract_assumptions(self, analysis: dict[str, Any]) -> list[str]:
        technical_constraints = analysis.get("technicalConstraints")
        if not isinstance(technical_constraints, dict):
            return []
        assumptions = technical_constraints.get("assumptions")
        if not isinstance(assumptions, list):
            return []
        return [str(assumption) for assumption in assumptions if str(assumption).strip()]

    def _build_change_set(
        self,
        *,
        project_id: str,
        source_message_id: str | None,
        extraction_result: Any,
        document_count: int,
    ) -> PendingChangeSetContract:
        created_at = datetime.now(timezone.utc).isoformat()
        requirements_payload = [
            requirement.model_dump(mode="json", by_alias=True, exclude_none=True)
            for requirement in extraction_result.requirements
        ]
        artifact_drafts = [
            {
                "id": str(uuid.uuid4()),
                "artifactType": ArtifactDraftType.REQUIREMENT.value,
                "artifactId": requirement.get("id"),
                "content": requirement,
            }
            for requirement in requirements_payload
        ]
        return PendingChangeSetContract(
            id=str(uuid.uuid4()),
            project_id=project_id,
            stage="extract_requirements",
            status=ChangeSetStatus.PENDING,
            created_at=created_at,
            source_message_id=source_message_id,
            bundle_summary=(
                f"Extracted {len(requirements_payload)} requirement(s) from "
                f"{document_count} document(s)"
            ),
            proposed_patch={"requirements": requirements_payload},
            artifact_drafts=artifact_drafts,
        )
