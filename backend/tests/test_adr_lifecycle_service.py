from __future__ import annotations

import pytest

from app.agents_system.services.aaa_state_models import stable_traceability_link_id
from app.features.agent.application.adr_lifecycle_service import (
    ADRLifecycleError,
    ADRLifecycleService,
)


def _citation(citation_id: str) -> dict[str, str]:
    return {
        "id": citation_id,
        "kind": "referenceDocument",
        "referenceDocumentId": f"ref-{citation_id}",
    }


def _id_factory() -> str:
    _id_factory.counter += 1
    return f"adr-{_id_factory.counter}"


_id_factory.counter = 0


def _now_factory() -> str:
    return "2026-04-08T12:00:00+00:00"


@pytest.fixture
def service() -> ADRLifecycleService:
    _id_factory.counter = 0
    return ADRLifecycleService(id_factory=_id_factory, now_factory=_now_factory)


def test_create_adr_appends_a_draft_with_normalized_traceability(service: ADRLifecycleService) -> None:
    updated_state, created = service.create_adr(
        state={"adrs": None, "traceabilityLinks": None},
        adr_payload={
            "title": " Adopt Azure Front Door ",
            "context": " Reduce regional failover time ",
            "decision": " Use Front Door Premium ",
            "consequences": " Adds managed edge cost ",
            "relatedRequirementIds": [" req-1 ", "", "req-2"],
            "relatedMindMapNodeIds": [" edge ", " "],
            "relatedWafEvidenceIds": [" waf-1 ", ""],
            "sourceCitations": [_citation("cite-1")],
        },
    )

    assert created["id"] == "adr-1"
    assert created["status"] == "draft"
    assert created["title"] == "Adopt Azure Front Door"
    assert created["relatedRequirementIds"] == ["req-1", "req-2"]
    assert created["relatedMindMapNodeIds"] == ["edge"]
    assert created["relatedWafEvidenceIds"] == ["waf-1"]
    assert created["createdAt"] == "2026-04-08T12:00:00+00:00"
    assert updated_state["adrs"] == [created]
    assert {link["id"] for link in updated_state["traceabilityLinks"]} == {
        stable_traceability_link_id(
            from_type="adr", from_id="adr-1", to_type="requirement", to_id="req-1"
        ),
        stable_traceability_link_id(
            from_type="adr", from_id="adr-1", to_type="requirement", to_id="req-2"
        ),
        stable_traceability_link_id(
            from_type="adr", from_id="adr-1", to_type="mindMapNode", to_id="edge"
        ),
        stable_traceability_link_id(
            from_type="adr", from_id="adr-1", to_type="wafEvidence", to_id="waf-1"
        ),
    }


def test_create_adr_ignores_caller_supplied_identity_status_and_created_at(
    service: ADRLifecycleService,
) -> None:
    _, created = service.create_adr(
        state={},
        adr_payload={
            "id": "caller-supplied-id",
            "status": "accepted",
            "createdAt": "1999-12-31T23:59:59+00:00",
            "title": "Normalize caller-controlled lifecycle metadata",
            "context": "The worker should not be able to inject identifiers or terminal states",
            "decision": "Lifecycle service owns the generated metadata",
            "consequences": "Prevents duplicate ids and invalid initial states",
            "relatedRequirementIds": ["req-10"],
            "sourceCitations": [_citation("cite-blank")],
            "missingEvidenceReason": "Diagram generation has not run yet.",
        },
    )

    assert created["id"] == "adr-1"
    assert created["status"] == "draft"
    assert created["createdAt"] == "2026-04-08T12:00:00+00:00"


def test_accept_adr_normalizes_existing_state_and_preserves_traceability(
    service: ADRLifecycleService,
) -> None:
    preserved_link = {
        "id": "manual-link",
        "fromType": "requirement",
        "fromId": "req-upstream",
        "toType": "diagram",
        "toId": "diag-7",
    }
    updated_state, accepted = service.accept_adr(
        state={
            "adrs": [
                {
                    "id": "adr-existing",
                    "title": " Keep hub-spoke ",
                    "status": "draft",
                    "context": " Existing landing zone ",
                    "decision": " Preserve hub-spoke topology ",
                    "consequences": " More firewall rules ",
                    "relatedRequirementIds": [" req-9 "],
                    "relatedMindMapNodeIds": ["networking"],
                    "sourceCitations": [_citation("cite-2")],
                    "missingEvidenceReason": "Diagram is scheduled for a later stage worker.",
                }
            ],
            "traceabilityLinks": [preserved_link],
        },
        adr_id="adr-existing",
    )

    assert accepted["status"] == "accepted"
    assert updated_state["adrs"] == [accepted]
    assert accepted["relatedRequirementIds"] == ["req-9"]
    assert preserved_link in updated_state["traceabilityLinks"]
    assert stable_traceability_link_id(
        from_type="adr",
        from_id="adr-existing",
        to_type="requirement",
        to_id="req-9",
    ) in {link["id"] for link in updated_state["traceabilityLinks"]}


def test_supersede_adr_marks_previous_and_inherits_traceability(service: ADRLifecycleService) -> None:
    updated_state, superseded, replacement = service.supersede_adr(
        state={
            "adrs": [
                {
                    "id": "adr-existing",
                    "title": "Adopt private endpoints",
                    "status": "accepted",
                    "context": "Security baseline",
                    "decision": "Use private endpoints for data plane services",
                    "consequences": "Extra DNS management",
                    "relatedRequirementIds": ["req-4"],
                    "relatedMindMapNodeIds": ["security"],
                    "relatedDiagramIds": ["diag-4"],
                    "sourceCitations": [_citation("cite-3")],
                    "createdAt": "2026-04-01T09:00:00+00:00",
                }
            ]
        },
        adr_id="adr-existing",
        replacement_payload={
            "title": "Adopt service endpoints",
            "context": "Private endpoint rollout is blocked",
            "decision": "Use service endpoints until DNS ownership is settled",
            "consequences": "Less isolation than private endpoints",
            "sourceCitations": [_citation("cite-4")],
        },
    )

    assert superseded["id"] == "adr-existing"
    assert superseded["status"] == "superseded"
    assert replacement["id"] == "adr-1"
    assert replacement["status"] == "accepted"
    assert replacement["supersedesAdrId"] == "adr-existing"
    assert replacement["relatedRequirementIds"] == ["req-4"]
    assert replacement["relatedMindMapNodeIds"] == ["security"]
    assert replacement["relatedDiagramIds"] == ["diag-4"]
    assert replacement["createdAt"] == "2026-04-08T12:00:00+00:00"
    assert updated_state["adrs"] == [superseded, replacement]
    assert stable_traceability_link_id(
        from_type="adr",
        from_id="adr-1",
        to_type="diagram",
        to_id="diag-4",
    ) in {link["id"] for link in updated_state["traceabilityLinks"]}


def test_supersede_adr_ignores_caller_supplied_identity_status_and_created_at(
    service: ADRLifecycleService,
) -> None:
    _, superseded, replacement = service.supersede_adr(
        state={
            "adrs": [
                {
                    "id": "adr-existing",
                    "title": "Adopt private endpoints",
                    "status": "accepted",
                    "context": "Security baseline",
                    "decision": "Use private endpoints for data plane services",
                    "consequences": "Extra DNS management",
                    "relatedRequirementIds": ["req-4"],
                    "sourceCitations": [_citation("cite-3")],
                    "missingEvidenceReason": "No diagram yet.",
                    "createdAt": "2026-04-01T09:00:00+00:00",
                }
            ]
        },
        adr_id="adr-existing",
        replacement_payload={
            "id": "caller-replacement-id",
            "status": "superseded",
            "createdAt": "2000-01-01T00:00:00+00:00",
            "title": "Replacement ADR",
            "context": "Need a new decision",
            "decision": "Move to service endpoints",
            "consequences": "Less isolation",
            "sourceCitations": [_citation("cite-4")],
        },
    )

    assert superseded["status"] == "superseded"
    assert replacement["id"] == "adr-1"
    assert replacement["status"] == "accepted"
    assert replacement["createdAt"] == "2026-04-08T12:00:00+00:00"


def test_accept_adr_rejects_invalid_transition(service: ADRLifecycleService) -> None:
    with pytest.raises(ADRLifecycleError, match="Cannot transition ADR 'adr-existing' from accepted to accepted"):
        service.accept_adr(
            state={
                "adrs": [
                    {
                        "id": "adr-existing",
                        "title": "Accepted ADR",
                        "status": "accepted",
                        "context": "ctx",
                        "decision": "decision",
                        "consequences": "cons",
                        "relatedRequirementIds": ["req-1"],
                        "sourceCitations": [_citation("cite-5")],
                        "missingEvidenceReason": "No diagram yet.",
                    }
                ]
            },
            adr_id="adr-existing",
        )


def test_create_adr_tolerates_malformed_existing_adrs(service: ADRLifecycleService) -> None:
    updated_state, created = service.create_adr(
        state={
            "adrs": [
                {
                    "id": "legacy-bad",
                    "title": "Legacy ADR without citations",
                    "status": "accepted",
                    "context": "Pre-service legacy data",
                    "decision": "Keep the old blob as-is",
                    "consequences": "Missing validator-required fields",
                    "relatedRequirementIds": [],
                    "sourceCitations": [],
                }
            ]
        },
        adr_payload={
            "title": "Add a valid ADR beside malformed legacy data",
            "context": "New worker paths should not brick on old state",
            "decision": "Preserve malformed entries and append validated ADRs",
            "consequences": "Legacy cleanup can happen separately",
            "relatedRequirementIds": ["req-20"],
            "sourceCitations": [_citation("cite-legacy")],
            "missingEvidenceReason": "No diagrams exist yet.",
        },
    )

    assert updated_state["adrs"][0]["id"] == "legacy-bad"
    assert created["id"] == "adr-1"
    assert updated_state["adrs"][1] == created


def test_reject_adr_marks_draft_as_rejected(service: ADRLifecycleService) -> None:
    updated_state, rejected = service.reject_adr(
        state={
            "adrs": [
                {
                    "id": "adr-existing",
                    "title": "Rejected ADR",
                    "status": "draft",
                    "context": "The option is still being evaluated",
                    "decision": "Option under review",
                    "consequences": "Need an explicit rejection path",
                    "relatedRequirementIds": ["req-30"],
                    "sourceCitations": [_citation("cite-reject")],
                    "missingEvidenceReason": "No diagram yet.",
                }
            ]
        },
        adr_id="adr-existing",
    )

    assert rejected["status"] == "rejected"
    assert updated_state["adrs"] == [rejected]
