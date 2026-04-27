from __future__ import annotations

from app.agents_system.contracts.stream_events import (
    FinalStreamEventPayload,
    TextStreamEventPayload,
    ToolCallStreamEventPayload,
    serialize_sse_event,
)
from app.agents_system.contracts.workflow_result import (
    ClarificationQuestionPayloadItem,
    ClarificationQuestionsPayload,
    NextStepProposal,
    StageClassification,
    ToolCallTrace,
    WorkflowCitation,
    WorkflowStageResult,
)


def test_workflow_stage_result_serializes_stage_classification() -> None:
    result = WorkflowStageResult(
        stage="clarify",
        stage_classification=StageClassification(
            stage="clarify",
            confidence=0.74,
            source="state_gaps",
            rationale="Open clarification questions remain unresolved.",
        ),
        summary="Need two clarification answers before proceeding.",
        pending_change_set=None,
        citations=[],
        warnings=[],
        next_step=NextStepProposal(
            stage="clarify",
            tool=None,
            rationale="The architect needs to answer the open questions before planning can continue.",
            blocking_questions=["Which tenant owns partner identities?"],
        ),
        reasoning_summary="Grouped the highest-impact questions by theme.",
        tool_calls=[],
    )

    payload = result.model_dump(mode="json", by_alias=True)

    assert payload["stageClassification"] == {
        "stage": "clarify",
        "confidence": 0.74,
        "source": "state_gaps",
        "rationale": "Open clarification questions remain unresolved.",
    }


def test_workflow_stage_result_serializes_optional_and_empty_fields() -> None:
    result = WorkflowStageResult(
        stage="clarify",
        summary="Need two clarification answers before proceeding.",
        pending_change_set=None,
        citations=[],
        warnings=[],
        next_step=NextStepProposal(
            stage="clarify",
            tool=None,
            rationale="The architect needs to answer the open questions before planning can continue.",
            blocking_questions=["Which tenant owns partner identities?"],
        ),
        reasoning_summary="Grouped the highest-impact questions by theme.",
        tool_calls=[],
        structured_payload=ClarificationQuestionsPayload(
            questions=[
                ClarificationQuestionPayloadItem(
                    id="security-1",
                    text="Which tenant owns partner identities?",
                    theme="Security",
                    why_it_matters="Identity boundaries drive RBAC and network isolation.",
                    architectural_impact="high",
                    priority=1,
                    related_requirement_ids=["req-auth"],
                )
            ]
        ),
    )

    payload = result.model_dump(mode="json", by_alias=True)

    assert payload["pendingChangeSet"] is None
    assert payload["citations"] == []
    assert payload["structuredPayload"] == {
        "type": "clarification_questions",
        "questions": [
            {
                "id": "security-1",
                "text": "Which tenant owns partner identities?",
                "theme": "Security",
                "whyItMatters": "Identity boundaries drive RBAC and network isolation.",
                "architecturalImpact": "high",
                "priority": 1,
                "relatedRequirementIds": ["req-auth"],
                "affectedDecision": None,
                "defaultAssumption": None,
                "riskIfWrong": None,
            }
        ],
    }


def test_workflow_stage_result_serializes_tool_traces_and_citations() -> None:
    result = WorkflowStageResult(
        stage="propose_candidate",
        summary="Compared two hosting patterns.",
        pending_change_set=None,
        citations=[
            WorkflowCitation(
                title="App Service landing zone guidance",
                url="https://learn.microsoft.com/azure/app-service/overview",
                source="microsoft_docs_search",
            )
        ],
        warnings=["Architecture choice is still pending."],
        next_step=NextStepProposal(
            stage="propose_candidate",
            tool="microsoft_docs_search",
            rationale="The architect should choose one option before applying state updates.",
            blocking_questions=["Which hosting model should we prefer?"],
        ),
        reasoning_summary="Used Microsoft Learn guidance to compare trade-offs.",
        tool_calls=[
            ToolCallTrace(
                tool_name="microsoft_docs_search",
                args_preview='{"query":"Azure App Service vs AKS"}',
                result_preview="Matched App Service overview and AKS baseline guidance.",
                citations=["https://learn.microsoft.com/azure/app-service/overview"],
                duration_ms=0,
            )
        ],
    )

    payload = result.model_dump(mode="json", by_alias=True)

    assert payload["citations"] == [
        {
            "title": "App Service landing zone guidance",
            "url": "https://learn.microsoft.com/azure/app-service/overview",
            "source": "microsoft_docs_search",
        }
    ]
    assert payload["toolCalls"] == [
        {
            "toolName": "microsoft_docs_search",
            "argsPreview": '{"query":"Azure App Service vs AKS"}',
            "resultPreview": "Matched App Service overview and AKS baseline guidance.",
            "citations": ["https://learn.microsoft.com/azure/app-service/overview"],
            "durationMs": 0,
        }
    ]


def test_stream_event_serialization_supports_canonical_payloads() -> None:
    final_event = serialize_sse_event(
        "final",
        FinalStreamEventPayload(
            answer="Hello",
            success=True,
            project_state={"projectId": "proj-1"},
            reasoning_steps=[],
            error=None,
            thread_id="thread-1",
            workflow_result=WorkflowStageResult(
                stage="clarify",
                summary="Hello",
                pending_change_set=None,
                citations=[],
                warnings=[],
                next_step=NextStepProposal(
                    stage="clarify",
                    tool=None,
                    rationale="Answer the clarification question before continuing.",
                    blocking_questions=["Which tenant?"],
                ),
                reasoning_summary="Hello",
                tool_calls=[],
                structured_payload=ClarificationQuestionsPayload(
                    questions=[
                        ClarificationQuestionPayloadItem(
                            id="security-1",
                            text="Which tenant?",
                            theme="Security",
                            why_it_matters="Tenant boundaries drive identity design.",
                            architectural_impact="high",
                            priority=1,
                            related_requirement_ids=["req-auth"],
                        )
                    ]
                ),
            ),
        ),
    )

    tool_call_event = serialize_sse_event(
        "tool_call",
        ToolCallStreamEventPayload(
            tool="microsoft_docs_search",
            args_preview='{"query":"Azure App Service"}',
        ),
    )
    text_event = serialize_sse_event("text", TextStreamEventPayload(delta="Hel"))

    assert final_event.startswith("event: final\ndata: {")
    assert '"workflow_result"' in final_event
    assert '"structuredPayload"' in final_event
    assert (
        tool_call_event
        == 'event: tool_call\ndata: {"tool": "microsoft_docs_search", "argsPreview": "{\\"query\\":\\"Azure App Service\\"}"}\n\n'
    )
    assert text_event == 'event: text\ndata: {"delta": "Hel"}\n\n'
