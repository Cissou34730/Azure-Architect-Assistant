import pytest
import uuid
from app.agents_system.checklists.normalize_helpers import (
    map_legacy_status, 
    map_normalized_status, 
    extract_waf_evaluations,
    reconstruct_legacy_waf_json
)
from app.models.checklist import ChecklistItem, ChecklistItemEvaluation, SeverityLevel
from datetime import datetime

def test_status_mapping():
    assert map_legacy_status("covered") == "fixed"
    assert map_legacy_status("partial") == "in_progress"
    assert map_legacy_status("notCovered") == "open"
    assert map_legacy_status("unknown") == "open"
    
    assert map_normalized_status("fixed") == "covered"
    assert map_normalized_status("in_progress") == "partial"
    assert map_normalized_status("open") == "notCovered"

def test_extract_waf_evaluations():
    legacy_state = {
        "wafChecklist": {
            "items": [
                {
                    "id": "waf-item-1",
                    "evaluations": [
                        {"id": "old-eval", "status": "notCovered", "evidence": "no"},
                        {"id": "new-eval", "status": "covered", "evidence": "yes", "created_at": "2024-01-01T00:00:00"}
                    ]
                }
            ]
        }
    }
    
    evals = extract_waf_evaluations(legacy_state)
    assert len(evals) == 1
    assert evals[0]["item_id"] == "waf-item-1"
    assert evals[0]["status"] == "fixed"
    assert "yes" in evals[0]["evidence"]["description"]
    assert evals[0]["evaluator"] == "legacy-migration"

def test_reconstruct_legacy_waf_json():
    item_id = uuid.uuid4()
    item = ChecklistItem(
        id=item_id,
        pillar="Security",
        template_item_id="waf-1",
        severity=SeverityLevel.MEDIUM,
        title="Secure everything"
    )
    evaluation = ChecklistItemEvaluation(
        id=uuid.uuid4(),
        item_id=item_id,
        project_id="proj-1",
        evaluator="test",
        source_type="test",
        status="fixed",
        evidence={"description": "done"},
        created_at=datetime(2024, 1, 1)
    )
    item.evaluations = [evaluation]
    
    legacy_json = reconstruct_legacy_waf_json("waf-2024", "1.0", [item])
    
    assert legacy_json["version"] == "1.0"
    assert "Security" in legacy_json["pillars"]
    assert len(legacy_json["items"]) == 1
    assert legacy_json["items"][0]["id"] == "waf-1"
    assert legacy_json["items"][0]["evaluations"][0]["status"] == "covered"
    assert legacy_json["items"][0]["evaluations"][0]["evidence"] == "done"
