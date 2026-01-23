import pytest
from pydantic import ValidationError

from app.agents_system.services.aaa_state_models import AAAProjectState


def _base_adr() -> dict:
    return {
        "id": "adr-1",
        "title": "Choose Cosmos DB for RAG memory",
        "status": "draft",
        "context": "We need low-latency global reads and simple ops.",
        "decision": "Use Cosmos DB as the primary store.",
        "consequences": "Need RU sizing and partitioning strategy.",
        "relatedRequirementIds": ["FR-001"],
        "sourceCitations": [
            {
                "id": "c1",
                "kind": "referenceDocument",
                "referenceDocumentId": "doc-1",
                "note": "Project requirements doc",
            }
        ],
    }


def test_adr_requires_requirement_link() -> None:
    state = {"adrs": [{**_base_adr(), "relatedRequirementIds": []}]}
    with pytest.raises(ValidationError):
        AAAProjectState.model_validate(state)


def test_adr_requires_evidence_or_reason() -> None:
    state = {"adrs": [_base_adr()]}
    with pytest.raises(ValidationError):
        AAAProjectState.model_validate(state)


def test_adr_accepts_missing_evidence_reason() -> None:
    adr = {**_base_adr(), "missingEvidenceReason": "Diagrams not generated yet."}
    state = {"adrs": [adr]}
    validated = AAAProjectState.model_validate(state)
    assert validated.adrs[0].missing_evidence_reason == "Diagrams not generated yet."


def test_adr_accepts_diagram_link_without_reason() -> None:
    adr = {**_base_adr(), "relatedDiagramIds": ["c4_context"]}
    state = {"adrs": [adr]}
    validated = AAAProjectState.model_validate(state)
    assert validated.adrs[0].related_diagram_ids == ["c4_context"]


def test_adr_requires_source_citation() -> None:
    state = {"adrs": [{**_base_adr(), "sourceCitations": []}], "traceabilityLinks": []}
    with pytest.raises(ValidationError):
        AAAProjectState.model_validate(state)

