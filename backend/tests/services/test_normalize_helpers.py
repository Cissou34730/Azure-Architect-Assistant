from app.agents_system.checklists.normalize_helpers import (
    merge_reconstructed_waf_payloads,
    validate_normalized_consistency,
)


def test_merge_reconstructed_waf_payloads_flattens_templates() -> None:
    reconstructed = {
        "azure-waf-v1": {
            "version": "1.0",
            "pillars": ["Security", "Reliability"],
            "items": [{"id": "sec-01"}, {"id": "rel-01"}],
        },
        "azure-waf-cost-v1": {
            "version": "1.0",
            "pillars": ["Cost", "Security"],
            "items": [{"id": "cost-01"}],
        },
    }

    merged = merge_reconstructed_waf_payloads(reconstructed)
    assert merged["version"] == "1.0"
    assert merged["pillars"] == ["Security", "Reliability", "Cost"]
    assert [item["id"] for item in merged["items"]] == ["sec-01", "rel-01", "cost-01"]


def test_validate_normalized_consistency_for_merged_shape() -> None:
    original = {
        "items": [{"id": "sec-01"}, {"id": "rel-01"}],
    }
    reconstructed = {
        "azure-waf-v1": {
            "items": [{"id": "sec-01"}, {"id": "rel-01"}],
        }
    }

    consistent, errors = validate_normalized_consistency(original, reconstructed)
    assert consistent is True
    assert errors == []


def test_validate_normalized_consistency_detects_missing_items() -> None:
    original = {
        "azure-waf-v1": {
            "items": [{"id": "sec-01"}, {"id": "rel-01"}],
        }
    }
    reconstructed = {
        "azure-waf-v1": {
            "items": [{"id": "sec-01"}],
        }
    }

    consistent, errors = validate_normalized_consistency(original, reconstructed)
    assert consistent is False
    assert errors
