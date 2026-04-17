"""
Stage routing and retry nodes for LangGraph workflow.

Phase 5: Add explicit stage routing and retry semantics.
"""

import logging
from enum import Enum
from typing import Any, Literal

from app.agents_system.contracts import StageClassification

from ..state import GraphState

logger = logging.getLogger(__name__)

COMPLEXITY_THRESHOLD = 3

_NON_ARCH_INTENT_KEYWORDS = [
    "waf",
    "checklist",
    "validate",
    "validation",
    "security benchmark",
    "aaa_record_validation_results",
    "adr",
    "decision",
    "cost",
    "price",
    "pricing",
    "budget",
    "terraform",
    "bicep",
    "iac",
    "infrastructure as code",
]

_ARTIFACT_EDIT_VERBS = (
    "update",
    "edit",
    "modify",
    "change",
    "revise",
    "refresh",
)

_ARTIFACT_EDIT_TARGETS = (
    "artifact",
    "artifacts",
    "requirement",
    "requirements",
    "assumption",
    "assumptions",
    "clarification question",
    "clarification questions",
    "candidate architecture",
    "candidate architectures",
    "diagram",
    "diagrams",
    "traceability",
)

_ARCHITECTURE_KEYWORDS = (
    "architecture",
    "architectural",
    "design",
    "candidate",
    "topology",
    "blueprint",
    "landing zone",
    "propose",
    "suggest architecture",
    "draw",
    "diagram",
    "c4",
    "container diagram",
    "system context",
)

_VALIDATE_KEYWORDS = (
    "validate",
    "validation",
    "waf",
    "compliance",
    "benchmark",
    "assess",
    "review security posture",
)

_PRICING_KEYWORDS = (
    "cost",
    "price",
    "pricing",
    "budget",
    "estimate",
    "how much",
    "tco",
    "total cost of ownership",
    "monthly total",
    "annual total",
)

_IAC_KEYWORDS = (
    "terraform",
    "bicep",
    "iac",
    "infrastructure as code",
    "deployment template",
    "arm template",
    "module",
)

_EXPORT_KEYWORDS = (
    "export",
    "document",
    "report",
    "summary",
)

_REVIEW_KEYWORDS = (
    "code review",
    "review the adr",
    "review adr",
    "peer review",
)

_ADR_KEYWORDS = (
    "adr",
    "decision",
    "architecture decision",
)


class ProjectStage(str, Enum):
    """Project workflow stages."""

    GENERAL = "general"
    EXTRACT_REQUIREMENTS = "extract_requirements"
    CLARIFY = "clarify"
    PROPOSE_CANDIDATE = "propose_candidate"
    MANAGE_ADR = "manage_adr"
    VALIDATE = "validate"
    PRICING = "pricing"
    IAC = "iac"
    EXPORT = "export"


def classify_next_stage(state: GraphState) -> dict[str, Any]:
    """Classify which stage should be executed next."""
    user_message = _normalize_text(state.get("user_message"))
    project_state = state.get("current_project_state") or {}
    agent_output = _normalize_text(state.get("agent_output"))

    classification = _detect_intent_from_keywords(user_message, agent_output)
    if classification is None:
        classification = _detect_intent_from_state(project_state)

    logger.info(
        "Classified next stage: %s (confidence=%.2f, source=%s)",
        classification.stage,
        classification.confidence,
        classification.source,
    )
    return {
        "next_stage": classification.stage,
        "stage_classification": classification.model_dump(mode="json", by_alias=True),
    }


def _detect_intent_from_keywords(
    user_message: str,
    agent_output: str,
) -> StageClassification | None:
    """Detect intended stage from keywords in user message or agent output."""
    intent_rules = (
        (
            _has_review_intent(user_message),
            _build_classification(
                stage=ProjectStage.GENERAL,
                confidence=0.88,
                source="intent_rules",
                rationale="Detected review-oriented wording without IaC-specific generation intent.",
            ),
        ),
        (
            _has_explicit_artifact_edit_intent(user_message),
            _build_classification(
                stage=ProjectStage.GENERAL,
                confidence=0.86,
                source="intent_rules",
                rationale="Detected explicit artifact-edit intent that should stay in the general workflow.",
            ),
        ),
        (
            _contains_any(user_message, _ARCHITECTURE_KEYWORDS),
            _build_classification(
                stage=ProjectStage.PROPOSE_CANDIDATE,
                confidence=0.95,
                source="intent_rules",
                rationale="Matched architecture-design intent keywords in the user message.",
            ),
        ),
        (
            _contains_any(user_message, _PRICING_KEYWORDS),
            _build_classification(
                stage=ProjectStage.PRICING,
                confidence=0.93,
                source="intent_rules",
                rationale="Matched pricing-estimation intent keywords in the user message.",
            ),
        ),
        (
            _contains_iac_generation_intent(user_message),
            _build_classification(
                stage=ProjectStage.IAC,
                confidence=0.92,
                source="intent_rules",
                rationale="Matched infrastructure-as-code generation intent keywords in the user message.",
            ),
        ),
        (
            _contains_any(user_message, _VALIDATE_KEYWORDS),
            _build_classification(
                stage=ProjectStage.VALIDATE,
                confidence=0.9,
                source="intent_rules",
                rationale="Matched validation and compliance intent keywords in the user message.",
            ),
        ),
        (
            _contains_any(user_message, _ADR_KEYWORDS),
            _build_classification(
                stage=ProjectStage.MANAGE_ADR,
                confidence=0.89,
                source="intent_rules",
                rationale="Matched ADR and architectural decision intent keywords in the user message.",
            ),
        ),
        (
            _contains_any(user_message, _EXPORT_KEYWORDS),
            _build_classification(
                stage=ProjectStage.EXPORT,
                confidence=0.84,
                source="intent_rules",
                rationale="Matched export and reporting intent keywords in the user message.",
            ),
        ),
        (
            _contains_any(agent_output, ("candidate", "solution", "propose", "suggest")),
            _build_classification(
                stage=ProjectStage.PROPOSE_CANDIDATE,
                confidence=0.72,
                source="agent_output",
                rationale="Agent output already contains proposal language, so continue proposal work.",
            ),
        ),
    )

    for matched, classification in intent_rules:
        if matched:
            return classification

    return None


def _build_classification(
    *,
    stage: ProjectStage,
    confidence: float,
    source: Literal["agent_output", "intent_rules", "state_gaps"],
    rationale: str,
) -> StageClassification:
    return StageClassification(
        stage=stage.value,
        confidence=confidence,
        source=source,
        rationale=rationale,
    )


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _contains_any(text: str, keywords: tuple[str, ...] | list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _has_review_intent(user_message: str) -> bool:
    return _contains_any(user_message, _REVIEW_KEYWORDS) or (
        "review" in user_message and "adr" in user_message and not _contains_iac_generation_intent(user_message)
    )


def _contains_iac_generation_intent(user_message: str) -> bool:
    if "code review" in user_message:
        return False
    return _contains_any(user_message, _IAC_KEYWORDS)


def _has_explicit_artifact_edit_intent(user_message: str) -> bool:
    return any(verb in user_message for verb in _ARTIFACT_EDIT_VERBS) and any(
        target in user_message for target in _ARTIFACT_EDIT_TARGETS
    )


def _detect_intent_from_state(project_state: dict[str, Any]) -> StageClassification:
    """Detect next stage based on gaps in current project state."""
    if _has_parsed_documents(project_state) and not project_state.get("requirements"):
        return _build_classification(
            stage=ProjectStage.EXTRACT_REQUIREMENTS,
            confidence=0.82,
            source="state_gaps",
            rationale="Parsed documents exist, but canonical requirements have not been extracted yet.",
        )
    if _has_open_clarification_questions(project_state):
        return _build_classification(
            stage=ProjectStage.CLARIFY,
            confidence=0.74,
            source="state_gaps",
            rationale="Open clarification questions remain unresolved.",
        )

    requirements = [
        (
            "requirements",
            ProjectStage.CLARIFY,
            0.68,
            "Requirements are still missing from project state, so clarification should continue.",
        ),
        (
            "candidateArchitectures",
            ProjectStage.PROPOSE_CANDIDATE,
            0.7,
            "Requirements exist, but no candidate architecture has been proposed yet.",
        ),
        (
            "adrs",
            ProjectStage.MANAGE_ADR,
            0.69,
            "Candidate architecture exists, but key decisions are not yet captured as ADRs.",
        ),
    ]

    for field, stage, confidence, rationale in requirements:
        if not project_state.get(field):
            return _build_classification(
                stage=stage,
                confidence=confidence,
                source="state_gaps",
                rationale=rationale,
            )

    waf = project_state.get("wafChecklist") or {}
    if not project_state.get("findings") or not waf:
        return _build_classification(
            stage=ProjectStage.VALIDATE,
            confidence=0.71,
            source="state_gaps",
            rationale="Validation findings or checklist evidence are still missing from project state.",
        )

    post_validation = [
        (
            "costEstimates",
            ProjectStage.PRICING,
            0.67,
            "Validation is complete, but baseline pricing has not been captured yet.",
        ),
        (
            "iacArtifacts",
            ProjectStage.IAC,
            0.67,
            "Validation is complete, but IaC artifacts have not been generated yet.",
        ),
    ]

    for field, stage, confidence, rationale in post_validation:
        if not project_state.get(field):
            return _build_classification(
                stage=stage,
                confidence=confidence,
                source="state_gaps",
                rationale=rationale,
            )

    return _build_classification(
        stage=ProjectStage.CLARIFY,
        confidence=0.55,
        source="state_gaps",
        rationale="No stronger state gap was detected, so continue with clarification.",
    )


def _has_parsed_documents(project_state: dict[str, Any]) -> bool:
    reference_documents = project_state.get("referenceDocuments")
    if isinstance(reference_documents, list):
        for document in reference_documents:
            if not isinstance(document, dict):
                continue
            parse_status = str(document.get("parseStatus") or document.get("parse_status") or "").lower()
            if parse_status == "parsed":
                return True

    project_document_stats = project_state.get("projectDocumentStats") or project_state.get("ingestionStats")
    if isinstance(project_document_stats, dict):
        parsed_documents = project_document_stats.get("parsedDocuments")
        if isinstance(parsed_documents, int) and parsed_documents > 0:
            return True

    return False


def _has_open_clarification_questions(project_state: dict[str, Any]) -> bool:
    clarification_questions = project_state.get("clarificationQuestions")
    if not isinstance(clarification_questions, list):
        return False

    for question in clarification_questions:
        if not isinstance(question, dict):
            continue
        if not str(question.get("question") or "").strip():
            continue
        status = str(question.get("status") or "open").strip().lower()
        if status not in {"answered", "resolved", "closed"}:
            return True
    return False


def check_for_retry(state: GraphState) -> Literal["retry", "continue"]:
    """Check if agent output requires a retry."""
    agent_output = state.get("agent_output", "")
    retry_count = state.get("retry_count", 0)

    if agent_output.strip().startswith("ERROR:") and retry_count < 1:
        logger.warning("Error detected in agent output, suggesting retry")
        return "retry"

    return "continue"


def build_retry_prompt(state: GraphState) -> dict[str, Any]:
    """Build a retry prompt asking for missing fields."""
    agent_output = state.get("agent_output", "")
    retry_count = state.get("retry_count", 0)

    error_lines = [line for line in agent_output.split("\n") if line.strip().startswith("ERROR:")]
    error_message = error_lines[0] if error_lines else "An error occurred"

    retry_prompt = (
        f"{error_message}\n\n"
        "Please provide the missing information or clarify your request."
    )

    logger.info("Built retry prompt (attempt %d)", retry_count + 1)
    return {
        "agent_output": retry_prompt,
        "retry_count": retry_count + 1,
    }


def _generate_next_step_questions(current_state: dict[str, Any]) -> list[str]:
    """Generate high-impact follow-up questions based on missing project artifacts."""
    questions = []
    if not current_state.get("candidateArchitectures"):
        questions.append(
            "Should we propose 1-2 candidate Azure architectures and generate the first C4 L1 diagram?"
        )
    if not current_state.get("adrs"):
        questions.append(
            "Which decisions should be captured as ADRs with WAF or diagram evidence?"
        )
    if not current_state.get("findings") or not current_state.get("wafChecklist"):
        questions.append("Do you want validation against WAF + Azure Security Benchmark now?")
    if not current_state.get("iacArtifacts"):
        questions.append("Should we generate Terraform/Bicep for the proposed components?")
    if not current_state.get("costEstimates"):
        questions.append("Do you need a cost estimate with key usage assumptions?")
    return questions[:5]


def propose_next_step(state: GraphState) -> dict[str, Any]:
    """Always propose next step if no artifact was persisted."""
    combined_updates = state.get("combined_updates", {})
    final_answer = state.get("final_answer", "")

    artifact_keys = [
        "candidateArchitectures",
        "adrs",
        "findings",
        "iacArtifacts",
        "costEstimates",
        "diagrams",
    ]
    if any(combined_updates.get(key) for key in artifact_keys):
        return {}

    questions = _generate_next_step_questions(state.get("current_project_state", {}))
    if not questions:
        return {}

    next_step_prompt = "\n\n**Next steps to consider:**\n" + "\n".join(
        [f"- {question}" for question in questions]
    )

    logger.info("Proposed %d next step questions", len(questions))
    return {
        "final_answer": final_answer + next_step_prompt,
    }



