from __future__ import annotations

from typing import Any

import pytest

from app.agents_system.config.prompt_loader import PromptLoader
from app.agents_system.langgraph.nodes.stage_routing import classify_next_stage
from app.features.agent.application.clarification_planner_worker import (
    ClarificationPlannerWorker,
)


@pytest.mark.asyncio
async def test_plan_questions_builds_stage_inputs_and_filters_history() -> None:
    captured_input: dict[str, Any] = {}

    async def _planner(planning_input: dict[str, Any]) -> dict[str, Any]:
        captured_input.update(planning_input)
        return {
            "questionGroups": [
                {
                    "theme": "Operations",
                    "questions": [
                        {
                            "question": "What RTO and RPO targets are required for the production workload?",
                            "whyItMatters": "Recovery objectives drive redundancy, replication, and backup design.",
                            "architecturalImpact": "high",
                            "priority": 2,
                            "relatedRequirementIds": ["req-dr"],
                        },
                        {
                            "question": "How will deployments be approved across production environments?",
                            "whyItMatters": "Operational controls shape release automation and environment isolation.",
                            "architecturalImpact": "medium",
                            "priority": 2,
                            "relatedRequirementIds": [],
                        },
                    ],
                },
                {
                    "theme": "Security",
                    "questions": [
                        {
                            "question": "Do partner users authenticate with your Entra tenant or with their own identities?",
                            "whyItMatters": "Identity boundaries determine tenant topology and access-control patterns.",
                            "architecturalImpact": "high",
                            "priority": 1,
                            "relatedRequirementIds": ["req-auth"],
                        },
                        {
                            "question": "Which regions are allowed for storing regulated audit data?",
                            "whyItMatters": "Region limits drive landing-zone, storage, and failover choices.",
                            "architecturalImpact": "high",
                            "priority": 3,
                            "relatedRequirementIds": ["req-dr"],
                        },
                        {
                            "question": "Do partner users authenticate with your Entra tenant or with their own identities?",
                            "whyItMatters": "Duplicate from prior history and should be removed.",
                            "architecturalImpact": "high",
                            "priority": 4,
                            "relatedRequirementIds": ["req-auth"],
                        },
                    ],
                },
                {
                    "theme": "Cost",
                    "questions": [
                        {
                            "question": "What monthly spend guardrail should the initial architecture stay within?",
                            "whyItMatters": "Budget limits influence service tiers and resiliency trade-offs.",
                            "architecturalImpact": "medium",
                            "priority": 1,
                            "relatedRequirementIds": [],
                        },
                        {
                            "question": "Should non-production environments scale to zero outside business hours?",
                            "whyItMatters": "Environment usage assumptions affect cost controls and platform choices.",
                            "architecturalImpact": "low",
                            "priority": 1,
                            "relatedRequirementIds": [],
                        },
                    ],
                },
            ]
        }

    worker = ClarificationPlannerWorker(planner=_planner)

    result = await worker.plan_questions(
        user_message="What else do you need before proposing the target Azure architecture?",
        current_state={
            "requirements": [
                {
                    "id": "req-auth",
                    "text": "Support partner sign-in with Microsoft identity services",
                    "category": "functional",
                    "ambiguity": {
                        "isAmbiguous": True,
                        "notes": "The identity boundary between host and partner tenants is unclear.",
                    },
                },
                {
                    "id": "req-dr",
                    "text": "Maintain business continuity for audit workflows",
                    "category": "nfr",
                    "ambiguity": {"isAmbiguous": False, "notes": ""},
                },
            ],
            "clarificationQuestions": [
                {
                    "id": "q-answered-1",
                    "question": "Do partner users authenticate with your Entra tenant or with their own identities?",
                    "status": "answered",
                }
            ],
            "pendingChangeSets": [
                {
                    "id": "pcs-1",
                    "stage": "clarify",
                    "proposedPatch": {
                        "clarificationQuestions": [
                            {
                                "id": "q-pending-1",
                                "question": "What retention period is required for audit logs?",
                                "status": "open",
                            }
                        ]
                    },
                }
            ],
            "wafChecklist": {
                "items": [
                    {
                        "id": "waf-sec-1",
                        "title": "Identity isolation strategy",
                        "pillar": "Security",
                        "evaluations": [{"status": "open"}],
                    },
                    {
                        "id": "waf-rel-1",
                        "title": "Geo-redundant recovery strategy",
                        "pillar": "Reliability",
                        "evaluations": [{"status": "in_progress"}],
                    },
                    {
                        "id": "waf-cost-1",
                        "title": "Cost guardrails",
                        "pillar": "Cost Optimization",
                        "evaluations": [{"status": "fixed"}],
                    },
                ]
            },
        },
        mindmap_coverage={
            "topics": {
                "identity": {"status": "partial"},
                "operations": {"status": "not-addressed"},
                "cost": {"status": "not-addressed"},
                "security": {"status": "addressed"},
            }
        },
    )

    assert captured_input["canonicalRequirements"][0]["id"] == "req-auth"
    assert captured_input["ambiguityMarkers"] == [
        {
            "requirementId": "req-auth",
            "requirementText": "Support partner sign-in with Microsoft identity services",
            "notes": "The identity boundary between host and partner tenants is unclear.",
        }
    ]
    assert [gap["itemId"] for gap in captured_input["wafGaps"]] == ["waf-sec-1", "waf-rel-1"]
    assert captured_input["mindmapGaps"] == [
        {"topic": "cost", "status": "not-addressed"},
        {"topic": "operations", "status": "not-addressed"},
        {"topic": "identity", "status": "partial"},
    ]
    assert {
        (item["question"], item["status"], item["source"])
        for item in captured_input["priorClarificationHistory"]
    } == {
        (
            "Do partner users authenticate with your Entra tenant or with their own identities?",
            "answered",
            "canonical",
        ),
        (
            "What retention period is required for audit logs?",
            "open",
            "pending",
        ),
    }

    total_questions = sum(len(group.questions) for group in result.question_groups)
    assert total_questions == 5
    assert [group.theme for group in result.question_groups] == ["Operations", "Security", "Cost"]
    flattened_questions = [
        question.question
        for group in result.question_groups
        for question in group.questions
    ]
    assert (
        "Do partner users authenticate with your Entra tenant or with their own identities?"
        not in flattened_questions
    )
    assert flattened_questions[0] == "What RTO and RPO targets are required for the production workload?"


@pytest.mark.asyncio
async def test_plan_questions_requires_actionable_output() -> None:
    async def _planner(_: dict[str, Any]) -> dict[str, Any]:
        return {"questionGroups": []}

    worker = ClarificationPlannerWorker(planner=_planner)

    with pytest.raises(ValueError, match="no actionable clarification questions"):
        await worker.plan_questions(
            user_message="Continue",
            current_state={},
            mindmap_coverage=None,
        )


def test_classify_next_stage_prefers_clarify_when_open_questions_exist() -> None:
    result = classify_next_stage(
        {
            "user_message": "Partners authenticate with their own Entra tenants.",
            "current_project_state": {
                "requirements": [{"id": "req-auth", "text": "Support partner sign-in"}],
                "clarificationQuestions": [
                    {
                        "id": "q-auth",
                        "question": "Do partners use their own tenant or a shared tenant?",
                        "status": "open",
                    }
                ],
            },
        }
    )

    assert result["next_stage"] == "clarify"
