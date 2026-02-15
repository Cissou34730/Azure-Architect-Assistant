import json

from app.agents_system.services.aaa_state_models import (
    apply_us6_enrichment,
    stable_traceability_link_id,
)
from app.agents_system.services.mindmap_loader import (
    REQUIRED_TOP_LEVEL_TOPIC_KEYS,
    update_mindmap_coverage,
)
from app.agents_system.tools.aaa_export_tool import AAAExportTool


def _extract_json_block(text: str) -> dict:
    start = text.index("```json\n") + len("```json\n")
    end = text.rindex("\n```")
    return json.loads(text[start:end])


def test_stable_traceability_link_id_is_deterministic() -> None:
    link_id_1 = stable_traceability_link_id(
        from_type="adr", from_id="a1", to_type="requirement", to_id="r1"
    )
    link_id_1_again = stable_traceability_link_id(
        from_type="adr", from_id="a1", to_type="requirement", to_id="r1"
    )
    link_id_2 = stable_traceability_link_id(
        from_type="adr", from_id="a1", to_type="requirement", to_id="r2"
    )

    assert link_id_1 == link_id_1_again
    assert link_id_1 != link_id_2


def test_apply_us6_enrichment_generates_links_without_duplicates() -> None:
    state = {
        "adrs": [
            {
                "id": "adr-1",
                "relatedRequirementIds": ["req-1"],
                "relatedMindMapNodeIds": ["node-1"],
                "relatedDiagramIds": ["diag-1"],
                "relatedWafEvidenceIds": [],
            }
        ],
        "findings": [
            {
                "id": "finding-1",
                "relatedRequirementIds": ["req-2"],
                "relatedAdrIds": ["adr-1"],
                "relatedDiagramIds": [],
                "relatedMindMapNodeIds": [],
            }
        ],
        "traceabilityLinks": [],
        "traceabilityIssues": [],
    }

    enriched_1 = apply_us6_enrichment(state)
    links_1 = enriched_1.get("traceabilityLinks")
    assert isinstance(links_1, list)
    assert len(links_1) == 5

    enriched_2 = apply_us6_enrichment(enriched_1)
    links_2 = enriched_2.get("traceabilityLinks")
    assert isinstance(links_2, list)
    assert len(links_2) == 5


def test_apply_us6_enrichment_records_duplicate_id_issue() -> None:
    duplicate_link = {
        "id": "dup",
        "fromType": "x",
        "fromId": "1",
        "toType": "y",
        "toId": "2",
    }
    state = {
        "traceabilityLinks": [duplicate_link, dict(duplicate_link)],
        "traceabilityIssues": [],
    }

    enriched = apply_us6_enrichment(state)
    issues = enriched.get("traceabilityIssues")
    assert isinstance(issues, list)
    assert any(i.get("kind") == "duplicate_link_id" for i in issues if isinstance(i, dict))


def test_update_mindmap_coverage_includes_all_required_topics() -> None:
    state = {"requirements": [{"id": "req-1"}]}
    updated = update_mindmap_coverage(state)
    coverage = updated.get("mindMapCoverage")
    assert isinstance(coverage, dict)
    topics = coverage.get("topics")
    assert isinstance(topics, dict)

    for key in REQUIRED_TOP_LEVEL_TOPIC_KEYS:
        assert key in topics

    assert topics["2_requirements_and_quality_attributes"]["status"] == "partial"
    assert topics["2_requirements_and_quality_attributes"]["confidence"] == 0.5


def test_update_mindmap_coverage_uses_waf_maturity_signal() -> None:
    state = {
        "wafChecklist": {
            "items": [
                {"id": "1", "evaluations": [{"status": "covered"}]},
                {"id": "2", "evaluations": [{"status": "partial"}]},
            ]
        }
    }

    updated = update_mindmap_coverage(state)
    topics = updated["mindMapCoverage"]["topics"]

    assert topics["8_security_and_compliance"]["status"] == "partial"
    assert topics["8_security_and_compliance"]["confidence"] == 0.5


def test_export_tool_returns_aaa_export_json_payload() -> None:
    tool = AAAExportTool()
    output = tool._run(
        exportFormat="json",
        state={"traceabilityLinks": [{"id": "l1", "fromType": "a", "fromId": "1", "toType": "b", "toId": "2"}]},
        pretty=False,
        fileName="aaa-export.json",
    )

    assert "AAA_EXPORT" in output
    payload = _extract_json_block(output)
    assert payload["state"]["traceabilityLinks"][0]["id"] == "l1"

