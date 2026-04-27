"""Worker helpers for approval-first clarification resolution bundles."""

from __future__ import annotations

import inspect
import json
import uuid
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timezone
from typing import Any, Protocol

from pydantic import ValidationError

from app.agents_system.config.prompt_loader import PromptLoader
from app.features.agent.contracts.clarification_resolution import (
    ClarificationResolutionResultContract,
)
from app.features.projects.contracts import (
    ArtifactDraftType,
    ChangeSetStatus,
    PendingChangeSetContract,
)
from app.shared.ai import llm_service
from app.shared.config.app_settings import get_app_settings


class PendingChangeRecorder(Protocol):
    async def record_pending_change(
        self,
        *,
        project_id: str,
        change_set: PendingChangeSetContract,
        db: object,
    ) -> PendingChangeSetContract: ...


class ClarificationResolutionWorker:
    """Resolve user clarification answers into a reviewable pending change set."""

    def __init__(
        self,
        *,
        resolver: Callable[[dict[str, Any]], Awaitable[dict[str, Any]] | dict[str, Any]] | None = None,
        pending_change_recorder: PendingChangeRecorder,
        prompt_loader: PromptLoader | None = None,
        change_set_id_factory: Callable[[], str] | None = None,
        artifact_id_factory: Callable[[], str] | None = None,
        assumption_id_factory: Callable[[], str] | None = None,
        now_factory: Callable[[], str] | None = None,
    ) -> None:
        self._resolver = resolver or self._resolve_with_llm
        self._pending_change_recorder = pending_change_recorder
        self._prompt_loader = prompt_loader or PromptLoader()
        self._change_set_id_factory = change_set_id_factory or (lambda: str(uuid.uuid4()))
        self._artifact_id_factory = artifact_id_factory or (lambda: str(uuid.uuid4()))
        self._assumption_id_factory = assumption_id_factory or (lambda: str(uuid.uuid4()))
        self._now_factory = now_factory or self._default_now_factory

    async def resolve_and_record_pending_change(
        self,
        *,
        project_id: str,
        user_message: str,
        project_state: Mapping[str, Any] | None,
        db: object,
        source_message_id: str | None = None,
    ) -> PendingChangeSetContract:
        resolution_input = self._build_resolution_input(
            user_message=user_message,
            project_state=project_state,
        )
        if not resolution_input["openClarificationQuestions"]:
            raise ValueError("No open clarification questions are available to resolve")

        resolution_result = self._resolver(resolution_input)
        if inspect.isawaitable(resolution_result):
            resolution_result = await resolution_result
        if not isinstance(resolution_result, dict):
            raise ValueError("Clarification resolver returned an invalid payload")

        try:
            normalized_result = ClarificationResolutionResultContract.model_validate(resolution_result)
        except ValidationError as exc:
            raise ValueError("Clarification resolver returned no actionable clarification updates") from exc

        change_set = self._build_change_set(
            project_id=project_id,
            source_message_id=source_message_id,
            project_state=project_state,
            resolution=normalized_result,
        )
        return await self._pending_change_recorder.record_pending_change(
            project_id=project_id,
            change_set=change_set,
            db=db,
        )

    def _build_resolution_input(
        self,
        *,
        user_message: str,
        project_state: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        state = dict(project_state or {})
        requirement_index = self._requirement_index(state)
        question_index = self._question_index(state)
        return {
            "userMessage": user_message.strip(),
            "canonicalRequirements": list(requirement_index.values()),
            "openClarificationQuestions": list(question_index.values()),
            "existingAssumptions": self._existing_assumptions(state),
        }

    def _requirement_index(self, project_state: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        requirements = project_state.get("requirements")
        if not isinstance(requirements, list):
            return {}

        indexed: dict[str, dict[str, Any]] = {}
        for requirement in requirements:
            if not isinstance(requirement, Mapping):
                continue
            requirement_id = str(requirement.get("id") or "").strip()
            text = str(requirement.get("text") or "").strip()
            if not requirement_id or not text:
                continue
            ambiguity = requirement.get("ambiguity")
            ambiguity_payload = ambiguity if isinstance(ambiguity, Mapping) else {}
            indexed[requirement_id] = {
                "id": requirement_id,
                "text": text,
                "category": requirement.get("category"),
                "ambiguity": {
                    "isAmbiguous": bool(ambiguity_payload.get("isAmbiguous")),
                    "notes": str(ambiguity_payload.get("notes") or "").strip(),
                },
            }
        return indexed

    def _question_index(self, project_state: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        questions = project_state.get("clarificationQuestions")
        if not isinstance(questions, list):
            return {}

        indexed: dict[str, dict[str, Any]] = {}
        for question in questions:
            if not isinstance(question, Mapping):
                continue
            question_id = str(question.get("id") or "").strip()
            question_text = str(question.get("question") or "").strip()
            status = str(question.get("status") or "open").strip().lower()
            if not question_id or not question_text or status in {"answered", "resolved", "closed"}:
                continue
            indexed[question_id] = {
                "id": question_id,
                "question": question_text,
                "status": status,
                "priority": question.get("priority"),
                "relatedRequirementIds": list(question.get("relatedRequirementIds") or []),
                # Preserved for the proceed-with-defaults path.
                "defaultAssumption": str(
                    question.get("defaultAssumption") or question.get("default_assumption") or ""
                ).strip(),
            }
        return indexed

    def _existing_assumptions(self, project_state: Mapping[str, Any]) -> list[dict[str, Any]]:
        assumptions = project_state.get("assumptions")
        if not isinstance(assumptions, list):
            return []

        normalized: list[dict[str, Any]] = []
        for assumption in assumptions:
            if not isinstance(assumption, Mapping):
                continue
            text = str(assumption.get("text") or "").strip()
            if not text:
                continue
            normalized.append(
                {
                    "id": assumption.get("id"),
                    "text": text,
                    "status": assumption.get("status"),
                    "relatedRequirementIds": list(assumption.get("relatedRequirementIds") or []),
                }
            )
        return normalized

    def _build_change_set(
        self,
        *,
        project_id: str,
        source_message_id: str | None,
        project_state: Mapping[str, Any] | None,
        resolution: ClarificationResolutionResultContract,
    ) -> PendingChangeSetContract:
        requirement_index = self._requirement_index(dict(project_state or {}))
        question_index = self._question_index(dict(project_state or {}))
        created_at = self._now_factory()

        requirement_payloads = [
            {
                "id": update.requirement_id,
                "text": update.text,
                "category": update.category or requirement_index.get(update.requirement_id, {}).get("category"),
                "ambiguity": {"isAmbiguous": False, "notes": ""},
            }
            for update in resolution.requirement_updates
        ]
        question_payloads = [
            {"id": update.question_id, "status": update.status}
            for update in resolution.question_updates
        ]
        assumption_payloads = [
            {
                "id": self._assumption_id_factory(),
                "text": assumption.text,
                "status": "open",
                "relatedRequirementIds": list(assumption.related_requirement_ids),
            }
            for assumption in resolution.assumptions
        ]

        artifact_drafts: list[dict[str, Any]] = []
        for update, requirement in zip(resolution.requirement_updates, requirement_payloads, strict=False):
            artifact_drafts.append(
                {
                    "id": self._artifact_id_factory(),
                    "artifactType": ArtifactDraftType.REQUIREMENT.value,
                    "artifactId": requirement["id"],
                    "content": {
                        **requirement,
                        "answerSummary": update.answer_summary,
                        "relatedQuestionIds": list(update.related_question_ids),
                    },
                    "createdAt": created_at,
                }
            )
        for update in resolution.question_updates:
            question_payload = dict(question_index.get(update.question_id) or {})
            artifact_drafts.append(
                {
                    "id": self._artifact_id_factory(),
                    "artifactType": ArtifactDraftType.CLARIFICATION_QUESTION.value,
                    "artifactId": update.question_id,
                    "content": {
                        **question_payload,
                        "id": update.question_id,
                        "status": update.status,
                        "answerSummary": update.answer_summary,
                        "relatedRequirementIds": list(update.related_requirement_ids),
                    },
                    "createdAt": created_at,
                }
            )
        for assumption in assumption_payloads:
            artifact_drafts.append(
                {
                    "id": self._artifact_id_factory(),
                    "artifactType": ArtifactDraftType.ASSUMPTION.value,
                    "artifactId": assumption["id"],
                    "content": assumption,
                    "createdAt": created_at,
                }
            )

        return PendingChangeSetContract(
            id=self._change_set_id_factory(),
            project_id=project_id,
            stage="clarify",
            status=ChangeSetStatus.PENDING,
            createdAt=created_at,
            source_message_id=source_message_id,
            bundleSummary=resolution.summary,
            proposedPatch={
                "_clarificationResolution": {
                    "requirements": requirement_payloads,
                    "clarificationQuestions": question_payloads,
                    "assumptions": assumption_payloads,
                }
            },
            artifactDrafts=artifact_drafts,
            citations=list(resolution.citations),
        )

    async def proceed_with_defaults(
        self,
        *,
        project_id: str,
        project_state: Mapping[str, Any] | None,
        db: object,
        source_message_id: str | None = None,
    ) -> PendingChangeSetContract:
        """Create a pending change set from default assumptions without an LLM call.

        Default assumptions are persisted as reviewable pending change artifacts so the user
        can inspect and approve them before they become canonical project state.
        """
        state = dict(project_state or {})
        question_index = self._question_index(state)

        if not question_index:
            raise ValueError("No open clarification questions available to proceed with defaults")

        created_at = self._now_factory()
        assumption_payloads: list[dict[str, Any]] = []
        question_payloads: list[dict[str, Any]] = []
        artifact_drafts: list[dict[str, Any]] = []

        for q_id, question in question_index.items():
            default_text = question.get("defaultAssumption") or ""
            if default_text:
                assumption_id = self._assumption_id_factory()
                assumption: dict[str, Any] = {
                    "id": assumption_id,
                    "text": default_text,
                    "status": "open",
                    "relatedRequirementIds": list(question.get("relatedRequirementIds") or []),
                }
                assumption_payloads.append(assumption)
                artifact_drafts.append(
                    {
                        "id": self._artifact_id_factory(),
                        "artifactType": ArtifactDraftType.ASSUMPTION.value,
                        "artifactId": assumption_id,
                        "content": assumption,
                        "createdAt": created_at,
                    }
                )
            question_payloads.append({"id": q_id, "status": "assumed"})

        change_set = PendingChangeSetContract(
            id=self._change_set_id_factory(),
            project_id=project_id,
            stage="clarify",
            status=ChangeSetStatus.PENDING,
            createdAt=created_at,
            source_message_id=source_message_id,
            bundleSummary="Proceeded with default assumptions for open clarification questions",
            proposedPatch={
                "_clarificationResolution": {
                    "requirements": [],
                    "clarificationQuestions": question_payloads,
                    "assumptions": assumption_payloads,
                }
            },
            artifactDrafts=artifact_drafts,
            citations=[],
        )
        return await self._pending_change_recorder.record_pending_change(
            project_id=project_id,
            change_set=change_set,
            db=db,
        )

    async def _resolve_with_llm(self, resolution_input: dict[str, Any]) -> dict[str, Any]:
        prompt_payload = json.dumps(resolution_input, ensure_ascii=False, indent=2)
        prompt_data = self._prompt_loader.load_prompt_file("clarification_resolution.yaml")
        system_prompt = str(prompt_data.get("system_prompt") or "").strip()
        system_prompt = (
            f"{system_prompt}\n\n"
            "Return JSON ONLY with this schema:\n"
            "{\n"
            '  "summary": "Short review summary",\n'
            '  "requirementUpdates": [\n'
            "    {\n"
            '      "requirementId": "req-1",\n'
            '      "text": "Updated requirement text",\n'
            '      "category": "functional | business | nfr",\n'
            '      "answerSummary": "How the user resolved the ambiguity",\n'
            '      "relatedQuestionIds": ["q-1"]\n'
            "    }\n"
            "  ],\n"
            '  "questionUpdates": [\n'
            "    {\n"
            '      "questionId": "q-1",\n'
            '      "status": "answered",\n'
            '      "answerSummary": "User answer summary",\n'
            '      "relatedRequirementIds": ["req-1"]\n'
            "    }\n"
            "  ],\n"
            '  "assumptions": [\n'
            "    {\n"
            '      "text": "New assumption inferred from the answer",\n'
            '      "relatedRequirementIds": ["req-1"]\n'
            "    }\n"
            "  ],\n"
            '  "citations": []\n'
            "}\n"
            "- Include only updates supported by the user reply.\n"
            "- Resolve requirement ambiguity by updating the requirement text and clearing ambiguity.\n"
            "- Only mark clarification questions as answered when the user reply clearly addresses them.\n"
            "- Do not invent new requirements when the user message is insufficient."
        ).strip()
        user_prompt = (
            "Resolve the latest clarification reply into a reviewable pending change bundle.\n\n"
            "Resolution input:\n"
            f"{prompt_payload}"
        )
        return await llm_service.get_llm_service()._complete_json(
            system_prompt,
            user_prompt,
            max_tokens=min(get_app_settings().llm_analyze_max_tokens, 4000),
        )

    @staticmethod
    def _default_now_factory() -> str:
        return datetime.now(timezone.utc).isoformat()


def create_clarification_resolution_worker() -> ClarificationResolutionWorker:
    """Build the shared clarification resolution worker."""
    from app.features.projects.application.chat_service import ChatService
    from app.features.projects.application.pending_changes_service import (
        ProjectPendingChangesService,
    )

    pending_changes_service = ProjectPendingChangesService(state_provider=ChatService())
    return ClarificationResolutionWorker(
        pending_change_recorder=pending_changes_service,
    )


__all__ = [
    "ClarificationResolutionWorker",
    "PendingChangeRecorder",
    "create_clarification_resolution_worker",
]

