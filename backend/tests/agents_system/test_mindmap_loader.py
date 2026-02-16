import json
from pathlib import Path
from typing import Any

import pytest

from app.agents_system.services.mindmap_loader import (
    MindMapValidationError,
    load_mindmap,
)

def _write_json(path: Path, content: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(content, handle)


def test_load_mindmap_accepts_direct_shape(tmp_path: Path) -> None:
    direct_file = tmp_path / "arch_mindmap.json"
    _write_json(
        direct_file,
        {
            "software_architecture_mindmap": {
                "1_foundations": {},
                "2_requirements_and_quality_attributes": {},
                "3_domain_and_design": {},
                "4_architecture_styles": {},
                "5_data_and_storage": {},
                "6_integration_and_distributed_systems": {},
                "7_cloud_and_infrastructure": {},
                "8_security_and_compliance": {},
                "9_delivery_and_lifecycle": {},
                "10_observability_and_reliability": {},
                "11_organization_and_process": {},
                "12_practice_ideas": {},
                "13_learning_and_practice": {},
            }
        },
    )

    result = load_mindmap(direct_file)

    assert "software_architecture_mindmap" in result.mindmap
    assert result.missing_top_level_keys == []


def test_load_mindmap_resolves_pointer_file(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    architecture_dir = docs_dir / "architecture"
    architecture_dir.mkdir(parents=True)

    pointer_file = docs_dir / "arch_mindmap.json"
    target_file = architecture_dir / "arch_mindmap.json"

    _write_json(
        pointer_file,
        {
            "status": "pointer",
            "movedTo": "./architecture/arch_mindmap.json",
        },
    )
    _write_json(
        target_file,
        {
            "software_architecture_mindmap": {
                "1_foundations": {},
                "2_requirements_and_quality_attributes": {},
                "3_domain_and_design": {},
                "4_architecture_styles": {},
                "5_data_and_storage": {},
                "6_integration_and_distributed_systems": {},
                "7_cloud_and_infrastructure": {},
                "8_security_and_compliance": {},
                "9_delivery_and_lifecycle": {},
                "10_observability_and_reliability": {},
                "11_organization_and_process": {},
                "12_practice_ideas": {},
                "13_learning_and_practice": {},
            }
        },
    )

    result = load_mindmap(pointer_file)

    assert "software_architecture_mindmap" in result.mindmap
    assert result.missing_top_level_keys == []


def test_load_mindmap_pointer_target_must_exist(tmp_path: Path) -> None:
    pointer_file = tmp_path / "arch_mindmap.json"
    _write_json(
        pointer_file,
        {
            "status": "pointer",
            "movedTo": "./architecture/arch_mindmap.json",
        },
    )

    with pytest.raises(MindMapValidationError, match="Mind map file not found"):
        load_mindmap(pointer_file)
