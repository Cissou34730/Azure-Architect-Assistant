"""Worker for structured clarification planning in the clarify stage."""

from __future__ import annotations

import inspect
import json
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import ValidationError

from app.agents_system.config.prompt_loader import PromptLoader
from app.features.agent.contracts.clarification_planner import (
    ClarificationPlanningResultContract,
    ClarificationQuestionContract,
    ClarificationQuestionGroupContract,
)
from app.shared.ai import llm_service
from app.shared.config.app_settings import get_app_settings

_IMPACT_RANK = {"high": 0, "medium": 1, "low": 2}
_RESOLVED_WAF_STATUSES = {"fixed", "false_positive", "done"}


class ClarificationPlannerWorker:
    """Plan high-value clarification questions from current project gaps."""

    def __init__(
        self,
        *,
        planner: Callable[[dict[str, Any]], Awaitable[dict[str, Any]] | dict[str, Any]] | None = None,
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        self._planner = planner or self._plan_with_llm
        self._prompt_loader = prompt_loader or PromptLoader()

    async def plan_questions(
        self,
        *,
        user_message: str,
        current_state: dict[str, Any],
        mindmap_coverage: dict[str, Any] | None,
    ) -> ClarificationPlanningResultContract:
        planning_input = self._build_planning_input(
            user_message=user_message,
            current_state=current_state,
            mindmap_coverage=mindmap_coverage,
        )
        planner_result = self._planner(planning_input)
        if inspect.isawaitable(planner_result):
            planner_result = await planner_result
        if not isinstance(planner_result, dict):
            raise ValueError("Clarification planner returned an invalid payload")

        try:
            normalized_result = ClarificationPlanningResultContract.model_validate(planner_result)
        except ValidationError as exc:
            raise ValueError(
                "Clarification planner returned no actionable clarification questions"
            ) from exc
        filtered_result = self._filter_and_prioritize(
            normalized_result,
            prior_history=planning_input["priorClarificationHistory"],
        )
        if not filtered_result.question_groups:
            raise ValueError("Clarification planner returned no actionable clarification questions")
        return filtered_result

    def _build_planning_input(
        self,
        *,
        user_message: str,
        current_state: dict[str, Any],
        mindmap_coverage: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "userMessage": user_message.strip(),
            "canonicalRequirements": self._build_requirement_inputs(current_state),
            "ambiguityMarkers": self._build_ambiguity_markers(current_state),
            "wafGaps": self._build_waf_gaps(current_state),
            "mindmapGaps": self._build_mindmap_gaps(current_state, mindmap_coverage),
            "priorClarificationHistory": self._build_prior_history(current_state),
        }

    def _build_requirement_inputs(self, current_state: dict[str, Any]) -> list[dict[str, Any]]:
        requirements = current_state.get("requirements")
        if not isinstance(requirements, list):
            return []

        normalized: list[dict[str, Any]] = []
        for requirement in requirements:
            if not isinstance(requirement, dict):
                continue
            text = str(requirement.get("text") or "").strip()
            if not text:
                continue
            normalized.append(
                {
                    "id": requirement.get("id"),
                    "text": text,
                    "category": requirement.get("category"),
                }
            )
        return normalized

    def _build_ambiguity_markers(self, current_state: dict[str, Any]) -> list[dict[str, Any]]:
        markers: list[dict[str, Any]] = []
        requirements = current_state.get("requirements")
        if not isinstance(requirements, list):
            return markers

        for requirement in requirements:
            if not isinstance(requirement, dict):
                continue
            ambiguity = requirement.get("ambiguity")
            if not isinstance(ambiguity, dict):
                continue
            notes = str(ambiguity.get("notes") or "").strip()
            is_ambiguous = bool(ambiguity.get("isAmbiguous")) or bool(notes)
            if not is_ambiguous:
                continue
            markers.append(
                {
                    "requirementId": requirement.get("id"),
                    "requirementText": str(requirement.get("text") or "").strip(),
                    "notes": notes,
                }
            )
        return markers

    def _build_waf_gaps(self, current_state: dict[str, Any]) -> list[dict[str, Any]]:
        waf_checklist = current_state.get("wafChecklist")
        if not isinstance(waf_checklist, dict):
            return []

        raw_items = waf_checklist.get("items")
        if isinstance(raw_items, dict):
            items = [item for item in raw_items.values() if isinstance(item, dict)]
        elif isinstance(raw_items, list):
            items = [item for item in raw_items if isinstance(item, dict)]
        else:
            items = []

        gaps: list[dict[str, Any]] = []
        for item in items:
            status = self._waf_item_status(item)
            if status in _RESOLVED_WAF_STATUSES:
                continue
            gaps.append(
                {
                    "itemId": item.get("id") or item.get("templateItemId"),
                    "title": item.get("title") or item.get("topic") or "Unnamed checklist item",
                    "pillar": item.get("pillar") or "Unknown",
                    "status": status,
                }
            )
        return gaps[:5]

    def _waf_item_status(self, item: dict[str, Any]) -> str:
        evaluations = item.get("evaluations")
        if isinstance(evaluations, list) and evaluations:
            latest = next(
                (
                    evaluation
                    for evaluation in reversed(evaluations)
                    if isinstance(evaluation, dict)
                ),
                None,
            )
            if latest is not None:
                return str(latest.get("status") or "open").strip().lower()
        return str(item.get("status") or "open").strip().lower()

    def _build_mindmap_gaps(
        self,
        current_state: dict[str, Any],
        mindmap_coverage: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        coverage = mindmap_coverage
        if not isinstance(coverage, dict):
            coverage = current_state.get("mindMapCoverage")
        if not isinstance(coverage, dict):
            return []

        topics = coverage.get("topics")
        if not isinstance(topics, dict):
            return []

        gap_items: list[dict[str, Any]] = []
        status_rank = {"not-addressed": 0, "partial": 1}
        for topic, details in topics.items():
            if not isinstance(details, dict):
                continue
            status = str(details.get("status") or "").strip().lower()
            if status not in status_rank:
                continue
            gap_items.append({"topic": str(topic), "status": status})

        gap_items.sort(key=lambda item: (status_rank[item["status"]], item["topic"]))
        return gap_items[:5]

    def _build_prior_history(self, current_state: dict[str, Any]) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        seen_questions: set[str] = set()

        def _append(question: str, status: str, source: str) -> None:
            normalized_question = self._normalize_question_text(question)
            if not normalized_question or normalized_question in seen_questions:
                return
            seen_questions.add(normalized_question)
            history.append({"question": question.strip(), "status": status, "source": source})

        canonical_questions = current_state.get("clarificationQuestions")
        if isinstance(canonical_questions, list):
            for question in canonical_questions:
                if not isinstance(question, dict):
                    continue
                text = str(question.get("question") or "").strip()
                if text:
                    _append(text, str(question.get("status") or "open"), "canonical")

        pending_change_sets = current_state.get("pendingChangeSets")
        if isinstance(pending_change_sets, list):
            for change_set in pending_change_sets:
                if not isinstance(change_set, dict):
                    continue
                if str(change_set.get("stage") or "").strip().lower() != "clarify":
                    continue

                proposed_patch = change_set.get("proposedPatch")
                if isinstance(proposed_patch, dict):
                    self._append_pending_questions(
                        proposed_patch.get("clarificationQuestions"),
                        _append,
                    )

                artifact_drafts = change_set.get("artifactDrafts")
                if isinstance(artifact_drafts, list):
                    for artifact in artifact_drafts:
                        if not isinstance(artifact, dict):
                            continue
                        if str(artifact.get("artifactType") or "").strip().lower() != "clarification_question":
                            continue
                        content = artifact.get("content")
                        if isinstance(content, dict):
                            self._append_pending_questions([content], _append)

        return history

    def _append_pending_questions(
        self,
        questions: Any,
        append: Callable[[str, str, str], None],
    ) -> None:
        if not isinstance(questions, list):
            return
        for question in questions:
            if not isinstance(question, dict):
                continue
            text = str(question.get("question") or "").strip()
            if text:
                append(text, str(question.get("status") or "open"), "pending")

    async def _plan_with_llm(self, planning_input: dict[str, Any]) -> dict[str, Any]:
        prompt_payload = json.dumps(planning_input, ensure_ascii=False, indent=2)
        prompt_data = self._prompt_loader.load_prompt_file("clarification_planner.yaml")
        system_prompt = str(prompt_data.get("system_prompt") or "").strip()
        system_prompt = (
            f"{system_prompt}\n\n"
            "Return JSON ONLY with this schema:\n"
            "{\n"
            '  "questionGroups": [\n'
            "    {\n"
            '      "theme": "Security",\n'
            '      "questions": [\n'
            "        {\n"
            '          "question": "Focused question",\n'
            '          "whyItMatters": "Why this matters for the architecture",\n'
            '          "architecturalImpact": "high | medium | low",\n'
            '          "priority": 1,\n'
            '          "relatedRequirementIds": ["req-1"]\n'
            "        }\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "- Limit the total response to 3-5 questions.\n"
            "- Group related questions under a single theme.\n"
            "- Prefer themes such as security, performance, reliability, cost, and operations.\n"
            "- When canonical requirements are empty, ask onboarding questions about workload type, scale, compliance, budget, and operations."
        ).strip()
        user_prompt = (
            "Plan the next clarification response for the Azure architecture workflow.\n\n"
            "Planning input:\n"
            f"{prompt_payload}"
        )
        return await llm_service.get_llm_service()._complete_json(
            system_prompt,
            user_prompt,
            max_tokens=min(get_app_settings().llm_analyze_max_tokens, 4000),
        )

    def _filter_and_prioritize(
        self,
        result: ClarificationPlanningResultContract,
        *,
        prior_history: list[dict[str, Any]],
    ) -> ClarificationPlanningResultContract:
        prior_questions = {
            self._normalize_question_text(str(item.get("question") or ""))
            for item in prior_history
        }
        seen_questions = set(prior_questions)

        flattened: list[tuple[str, ClarificationQuestionContract]] = []
        for group in result.question_groups:
            for question in group.questions:
                normalized_question = self._normalize_question_text(question.question)
                if not normalized_question or normalized_question in seen_questions:
                    continue
                seen_questions.add(normalized_question)
                flattened.append((group.theme, question))

        flattened.sort(
            key=lambda item: (
                _IMPACT_RANK[item[1].architectural_impact],
                item[1].priority,
                item[0].lower(),
                self._normalize_question_text(item[1].question),
            )
        )
        limited_questions = flattened[:5]

        grouped: dict[str, list[ClarificationQuestionContract]] = {}
        theme_order: list[str] = []
        for theme, question in limited_questions:
            if theme not in grouped:
                grouped[theme] = []
                theme_order.append(theme)
            grouped[theme].append(question)

        return ClarificationPlanningResultContract(
            question_groups=[
                ClarificationQuestionGroupContract(theme=theme, questions=grouped[theme])
                for theme in theme_order
            ]
        )

    def _normalize_question_text(self, question: str) -> str:
        return " ".join(question.strip().lower().split())

