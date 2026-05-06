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
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(classify_next_stage(
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
    ))

    assert result["next_stage"] == "clarify"


def test_clarification_prompt_has_required_question_structure() -> None:
    """Each clarification question must advertise its decision impact, default, and risk."""
    loader = PromptLoader()
    prompt_data = loader.load_prompt_file("clarification_planner.yaml")
    prompt = prompt_data.get("system_prompt", "")
    prompt_lower = prompt.lower()
    assert "why_it_matters" in prompt or "why it matters" in prompt_lower
    assert "affected_decision" in prompt or "affected decision" in prompt_lower
    assert "default_assumption" in prompt or "default assumption" in prompt_lower
    assert "risk_if_wrong" in prompt or "risk if wrong" in prompt_lower


def test_clarification_limits_to_top_questions() -> None:
    """The prompt must restrict the response to 3-5 high-impact questions."""
    loader = PromptLoader()
    prompt_data = loader.load_prompt_file("clarification_planner.yaml")
    prompt = prompt_data.get("system_prompt", "")
    assert "3 to 5" in prompt or "3-5" in prompt or "top 3" in prompt


# ─── Q0.1 — Customer question quality regression tests ────────────────────────


@pytest.mark.asyncio
async def test_customer_clarification_excludes_implementation_choice_questions() -> None:
    """Customer questions must focus on requirement clarification, not solution choices.

    Questions like 'Should we use Azure Front Door' prescribe implementation and
    must NOT appear in customerClarificationGroups.
    """

    async def _planner(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "customerClarificationGroups": [
                {
                    "theme": "Compliance",
                    "questions": [
                        {
                            "question": "The documents mention EU data residency but also a US-only support team. Can support staff access production customer data from outside the EU?",
                            "whyItMatters": "Determines data residency compliance requirements.",
                            "clarificationTarget": "conflict",
                            "sourceRefs": ["req-compliance"],
                        },
                        {
                            "question": "Should we use Azure Front Door or API Management for the public-facing entry point?",
                            "whyItMatters": "Affects latency and DDoS protection.",
                            "clarificationTarget": "missing",
                            "sourceRefs": [],
                        },
                    ],
                },
                {
                    "theme": "Scale",
                    "questions": [
                        {
                            "question": "Which tier should we use for Azure Kubernetes Service — Standard or Premium?",
                            "whyItMatters": "Affects SLA and cost.",
                            "clarificationTarget": "missing",
                            "sourceRefs": [],
                        },
                        {
                            "question": "Are there peak usage patterns or scale targets defined in the compliance documents?",
                            "whyItMatters": "Missing scale targets make it impossible to validate capacity.",
                            "clarificationTarget": "missing",
                            "sourceRefs": ["req-scale"],
                        },
                    ],
                },
            ],
            "architectQuestionGroups": [
                {
                    "theme": "Security",
                    "questions": [
                        {
                            "question": "How will the design prove tenant isolation across identity, data storage, and observability boundaries?",
                            "designDecision": "identity topology",
                            "coverageSources": [{"kind": "waf", "id": "waf-sec-1", "pillar": "Security"}],
                            "riskIfUnanswered": "Architecture may not prove tenant isolation.",
                            "recommendedEvidence": ["identity flow", "RBAC matrix"],
                            "status": "open",
                            "answer": None,
                            "answeredAt": None,
                            "answerSource": None,
                        }
                    ],
                }
            ],
        }

    worker = ClarificationPlannerWorker(planner=_planner)
    result = await worker.plan_questions(
        user_message="What clarifications do you need?",
        current_state={},
        mindmap_coverage=None,
    )

    # The new result must expose customer clarification groups (AttributeError with current code)
    customer_groups = result.customer_clarification_groups

    customer_questions = [
        q.question
        for group in customer_groups
        for q in group.questions
    ]

    # Implementation-prescriptive phrases must be filtered out
    implementation_phrases = [
        "Should we use Azure Front Door",
        "Which tier should we",
        "Which Azure service",
        "Should we use private endpoints",
    ]
    for phrase in implementation_phrases:
        assert not any(phrase.lower() in q.lower() for q in customer_questions), (
            f"Customer question contained implementation choice phrase: '{phrase}'"
        )

    # Requirement-clarification questions must be preserved
    assert any("EU data residency" in q for q in customer_questions)
    assert any("scale targets" in q.lower() for q in customer_questions)


@pytest.mark.asyncio
async def test_customer_questions_reject_azure_service_selection_phrases() -> None:
    """Customer question groups must not surface 'Which Azure service' or 'Should we use X' questions."""

    async def _planner(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "customerClarificationGroups": [
                {
                    "theme": "Requirements",
                    "questions": [
                        {
                            "question": "Which Azure service should handle the primary ingestion pipeline?",
                            "whyItMatters": "Drives compute and networking topology.",
                            "clarificationTarget": "missing",
                            "sourceRefs": [],
                        },
                        {
                            "question": "Are conflicting availability requirements between the mobile app (99.9%) and the batch reporting system (95%) intentional?",
                            "whyItMatters": "Conflicting SLAs require business prioritisation before design.",
                            "clarificationTarget": "conflict",
                            "sourceRefs": ["req-availability"],
                        },
                    ],
                }
            ],
            "architectQuestionGroups": [
                {
                    "theme": "Reliability",
                    "questions": [
                        {
                            "question": "How will the design satisfy the 99.9% SLA for the mobile app while allowing 95% for batch processing?",
                            "designDecision": "reliability tier",
                            "coverageSources": [{"kind": "waf", "id": "waf-rel-1", "pillar": "Reliability"}],
                            "riskIfUnanswered": "Conflicting SLAs may result in over-engineered batch workloads.",
                            "recommendedEvidence": ["SLA breakdown", "failure mode analysis"],
                            "status": "open",
                            "answer": None,
                            "answeredAt": None,
                            "answerSource": None,
                        }
                    ],
                }
            ],
        }

    worker = ClarificationPlannerWorker(planner=_planner)
    result = await worker.plan_questions(
        user_message="Any clarifications needed?",
        current_state={},
        mindmap_coverage=None,
    )

    # AttributeError with current code — new attribute does not exist yet
    customer_groups = result.customer_clarification_groups
    customer_questions = [
        q.question
        for group in customer_groups
        for q in group.questions
    ]

    assert not any("Which Azure service" in q for q in customer_questions)
    assert any("availability" in q.lower() for q in customer_questions)


# ─── Q0.2 — Two output sets tests ─────────────────────────────────────────────


def test_clarification_planning_result_contract_parses_split_shape() -> None:
    """ClarificationPlanningResultContract must accept both customerClarificationGroups and architectQuestionGroups."""
    from app.features.agent.contracts.clarification_planner import ClarificationPlanningResultContract

    raw = {
        "customerClarificationGroups": [
            {
                "theme": "Requirements",
                "questions": [
                    {
                        "question": "The documents mention EU data residency but also a US-only support team. Can support staff access production customer data from outside the EU?",
                        "whyItMatters": "Determines data residency compliance requirements.",
                        "clarificationTarget": "conflict",
                        "sourceRefs": ["req-compliance"],
                    }
                ],
            }
        ],
        "architectQuestionGroups": [
            {
                "theme": "Security",
                "questions": [
                    {
                        "question": "How will the design prove tenant isolation across identity, data storage, and observability boundaries?",
                        "designDecision": "identity topology",
                        "coverageSources": [{"kind": "waf", "id": "waf-sec-1", "pillar": "Security"}],
                        "riskIfUnanswered": "Architecture may not prove tenant isolation.",
                        "recommendedEvidence": ["identity flow", "RBAC matrix"],
                        "status": "open",
                        "answer": None,
                        "answeredAt": None,
                        "answerSource": None,
                    }
                ],
            }
        ],
    }

    # Must parse without error — currently fails: extra="forbid" rejects new fields,
    # and questionGroups (required) is absent.
    result = ClarificationPlanningResultContract.model_validate(raw)
    assert result.customer_clarification_groups is not None
    assert result.architect_question_groups is not None
    assert len(result.customer_clarification_groups) == 1
    assert len(result.architect_question_groups) == 1


def test_clarification_planning_result_contract_rejects_old_shape() -> None:
    """ClarificationPlanningResultContract with only questionGroups (old shape) must fail validation."""
    from app.features.agent.contracts.clarification_planner import ClarificationPlanningResultContract

    raw = {
        "questionGroups": [
            {
                "theme": "Security",
                "questions": [
                    {
                        "question": "Do partner users authenticate with your Entra tenant or their own?",
                        "whyItMatters": "Identity boundaries determine topology.",
                        "architecturalImpact": "high",
                        "priority": 1,
                    }
                ],
            }
        ]
    }

    # The new contract must require the split fields — currently PASSES (old shape is valid),
    # so this pytest.raises block will itself fail, making the test fail as expected.
    with pytest.raises(Exception):
        ClarificationPlanningResultContract.model_validate(raw)


@pytest.mark.asyncio
async def test_plan_questions_returns_both_customer_and_architect_groups() -> None:
    """worker.plan_questions must return a result with both customer and architect question groups."""

    async def _planner(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "customerClarificationGroups": [
                {
                    "theme": "Requirements",
                    "questions": [
                        {
                            "question": "The documents mention EU data residency but also a US-only support team. Can support staff access production customer data from outside the EU?",
                            "whyItMatters": "Determines data residency compliance requirements.",
                            "clarificationTarget": "conflict",
                            "sourceRefs": ["req-compliance"],
                        }
                    ],
                }
            ],
            "architectQuestionGroups": [
                {
                    "theme": "Security",
                    "questions": [
                        {
                            "question": "How will the design prove tenant isolation across identity, data storage, and observability boundaries?",
                            "designDecision": "identity topology",
                            "coverageSources": [{"kind": "waf", "id": "waf-sec-1", "pillar": "Security"}],
                            "riskIfUnanswered": "Architecture may not prove tenant isolation.",
                            "recommendedEvidence": ["identity flow", "RBAC matrix"],
                            "status": "open",
                            "answer": None,
                            "answeredAt": None,
                            "answerSource": None,
                        }
                    ],
                }
            ],
        }

    worker = ClarificationPlannerWorker(planner=_planner)
    result = await worker.plan_questions(
        user_message="What do you need?",
        current_state={},
        mindmap_coverage=None,
    )

    # Both sets must be accessible on the result object (AttributeError with current code)
    assert hasattr(result, "customer_clarification_groups"), "result missing customer_clarification_groups"
    assert hasattr(result, "architect_question_groups"), "result missing architect_question_groups"
    assert len(result.customer_clarification_groups) == 1
    assert len(result.architect_question_groups) == 1
    assert result.customer_clarification_groups[0].theme == "Requirements"
    assert result.architect_question_groups[0].theme == "Security"


# ─── Q0.3 — WAF / mindmap coverage tests for architect questions ───────────────


@pytest.mark.asyncio
async def test_architect_questions_reference_waf_gaps() -> None:
    """When WAF gaps exist, architect questions must reference them via coverageSources with kind='waf'."""
    waf_gap_id = "waf-sec-1"
    mindmap_gap_topic = "identity"

    async def _planner(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "customerClarificationGroups": [
                {
                    "theme": "Compliance",
                    "questions": [
                        {
                            "question": "Are there specific regulatory frameworks (e.g., GDPR, ISO 27001) that must be adhered to for the identity management system?",
                            "whyItMatters": "Regulatory requirements constrain identity topology choices.",
                            "clarificationTarget": "missing",
                            "sourceRefs": ["req-compliance"],
                        }
                    ],
                }
            ],
            "architectQuestionGroups": [
                {
                    "theme": "Security",
                    "questions": [
                        {
                            "question": "How will the design prove tenant isolation across identity, data storage, and observability boundaries?",
                            "designDecision": "identity topology",
                            "coverageSources": [
                                {"kind": "waf", "id": waf_gap_id, "pillar": "Security"},
                                {"kind": "mindmap", "id": mindmap_gap_topic},
                            ],
                            "riskIfUnanswered": "Architecture may not prove tenant isolation.",
                            "recommendedEvidence": ["identity flow", "RBAC matrix"],
                            "status": "open",
                            "answer": None,
                            "answeredAt": None,
                            "answerSource": None,
                        }
                    ],
                }
            ],
        }

    worker = ClarificationPlannerWorker(planner=_planner)
    result = await worker.plan_questions(
        user_message="What architecture questions remain?",
        current_state={
            "wafChecklist": {
                "items": [
                    {
                        "id": waf_gap_id,
                        "title": "Identity isolation strategy",
                        "pillar": "Security",
                        "evaluations": [{"status": "open"}],
                    }
                ]
            }
        },
        mindmap_coverage={
            "topics": {
                mindmap_gap_topic: {"status": "partial"},
            }
        },
    )

    # AttributeError with current code — new attribute does not exist yet
    architect_groups = result.architect_question_groups
    all_coverage_sources = [
        source
        for group in architect_groups
        for q in group.questions
        for source in q.coverage_sources
    ]

    waf_source_ids = {s.id for s in all_coverage_sources if s.kind == "waf"}
    mindmap_source_ids = {s.id for s in all_coverage_sources if s.kind == "mindmap"}

    assert waf_gap_id in waf_source_ids, (
        f"WAF gap '{waf_gap_id}' not referenced in architect questions"
    )
    assert mindmap_gap_topic in mindmap_source_ids, (
        f"Mindmap gap '{mindmap_gap_topic}' not referenced in architect questions"
    )


@pytest.mark.asyncio
async def test_architect_questions_reference_mindmap_gaps() -> None:
    """When mindmap gaps exist (partial/not-addressed topics), architect questions must reference them."""

    async def _planner(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "customerClarificationGroups": [
                {
                    "theme": "Operations",
                    "questions": [
                        {
                            "question": "Who owns the on-call rotation for production incidents — the product team or a dedicated SRE team?",
                            "whyItMatters": "Determines whether the architecture needs an SRE-friendly observability layer.",
                            "clarificationTarget": "missing",
                            "sourceRefs": [],
                        }
                    ],
                }
            ],
            "architectQuestionGroups": [
                {
                    "theme": "Operations",
                    "questions": [
                        {
                            "question": "What observability and alerting strategy will be used for the operations team?",
                            "designDecision": "monitoring architecture",
                            "coverageSources": [
                                {"kind": "mindmap", "id": "operations"},
                                {"kind": "mindmap", "id": "cost"},
                            ],
                            "riskIfUnanswered": "Operational gaps may remain invisible.",
                            "recommendedEvidence": ["alerting runbook", "dashboard mockup"],
                            "status": "open",
                            "answer": None,
                            "answeredAt": None,
                            "answerSource": None,
                        }
                    ],
                }
            ],
        }

    worker = ClarificationPlannerWorker(planner=_planner)
    result = await worker.plan_questions(
        user_message="Any architecture decisions pending?",
        current_state={},
        mindmap_coverage={
            "topics": {
                "operations": {"status": "not-addressed"},
                "cost": {"status": "not-addressed"},
                "identity": {"status": "addressed"},
            }
        },
    )

    # AttributeError with current code — new attribute does not exist yet
    architect_groups = result.architect_question_groups
    all_coverage_sources = [
        source
        for group in architect_groups
        for q in group.questions
        for source in q.coverage_sources
    ]

    mindmap_source_ids = {s.id for s in all_coverage_sources if s.kind == "mindmap"}
    assert "operations" in mindmap_source_ids
    assert "cost" in mindmap_source_ids


@pytest.mark.asyncio
async def test_waf_gaps_without_coverage_raises_or_marks_not_applicable() -> None:
    """If WAF gaps exist but no architect question covers them, the result must track them as uncovered.

    The worker must either raise a ValueError or surface an `uncovered_waf_gaps` attribute
    listing items that were neither covered by an architect question nor resolved.
    """
    uncovered_waf_id = "waf-rel-1"

    async def _planner(_: dict[str, Any]) -> dict[str, Any]:
        # Only waf-sec-1 is covered; waf-rel-1 is deliberately omitted from coverageSources.
        return {
            "customerClarificationGroups": [
                {
                    "theme": "Scale",
                    "questions": [
                        {
                            "question": "What are the expected peak concurrent users for the workload?",
                            "whyItMatters": "Scale targets drive compute and database tier selection.",
                            "clarificationTarget": "missing",
                            "sourceRefs": [],
                        }
                    ],
                }
            ],
            "architectQuestionGroups": [
                {
                    "theme": "Security",
                    "questions": [
                        {
                            "question": "How will the design prove tenant isolation?",
                            "designDecision": "identity topology",
                            "coverageSources": [
                                {"kind": "waf", "id": "waf-sec-1", "pillar": "Security"},
                            ],
                            "riskIfUnanswered": "Tenant isolation unproven.",
                            "recommendedEvidence": ["identity flow"],
                            "status": "open",
                            "answer": None,
                            "answeredAt": None,
                            "answerSource": None,
                        }
                    ],
                }
            ],
        }

    worker = ClarificationPlannerWorker(planner=_planner)
    result = await worker.plan_questions(
        user_message="What is left to decide?",
        current_state={
            "wafChecklist": {
                "items": [
                    {
                        "id": "waf-sec-1",
                        "title": "Identity isolation strategy",
                        "pillar": "Security",
                        "evaluations": [{"status": "open"}],
                    },
                    {
                        "id": uncovered_waf_id,
                        "title": "Geo-redundant recovery strategy",
                        "pillar": "Reliability",
                        "evaluations": [{"status": "open"}],
                    },
                ]
            }
        },
        mindmap_coverage=None,
    )

    # The uncovered WAF gap must be tracked on the result (AttributeError with current code)
    uncovered_ids = {gap.item_id for gap in result.uncovered_waf_gaps}
    assert uncovered_waf_id in uncovered_ids, (
        f"WAF gap '{uncovered_waf_id}' was neither covered by an architect question "
        "nor listed in result.uncovered_waf_gaps"
    )
