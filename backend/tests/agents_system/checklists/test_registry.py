import json
import pytest
from pathlib import Path
from app.agents_system.checklists.registry import ChecklistRegistry
from app.models.checklist import ChecklistTemplate
from app.core.app_settings import AppSettings

@pytest.fixture
def temp_cache_dir(tmp_path):
    d = tmp_path / "waf_templates"
    d.mkdir()
    return d

@pytest.fixture
def mock_settings():
    return AppSettings() # Uses defaults

def test_registry_load_empty(temp_cache_dir, mock_settings):
    registry = ChecklistRegistry(temp_cache_dir, mock_settings)
    assert len(registry.list_templates()) == 0

def test_registry_register_and_load(temp_cache_dir, mock_settings):
    registry = ChecklistRegistry(temp_cache_dir, mock_settings)
    
    template = ChecklistTemplate(
        slug="test-waf",
        title="Test WAF",
        version="1.0",
        content=[{"id": "item1", "title": "First Item"}]
    )
    
    registry.register_template(template)
    assert len(registry.list_templates()) == 1
    assert registry.get_template("test-waf").title == "Test WAF"
    
    # Check persistence
    assert (temp_cache_dir / "test-waf.json").exists()
    
    # New registry instance should load it
    new_registry = ChecklistRegistry(temp_cache_dir, mock_settings)
    assert len(new_registry.list_templates()) == 1
    assert new_registry.get_template("test-waf").content[0]["id"] == "item1"

def test_registry_invalid_json(temp_cache_dir, mock_settings):
    # Create invalid JSON
    (temp_cache_dir / "invalid.json").write_text("not json")
    (temp_cache_dir / "missing_fields.json").write_text(json.dumps({"slug": "missing"}))
    
    registry = ChecklistRegistry(temp_cache_dir, mock_settings)
    assert len(registry.list_templates()) == 0
