"""Unit tests for KBManager using tmp_path fixtures (no real data dirs)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.ai.config import AIConfig

# Patches applied before KBManager import resolves get_kb_storage_root
_MODULE = "app.kb.knowledge_base_manager"


def _write_config(config_path: Path, kbs: list[dict]) -> None:
    config_path.write_text(json.dumps({"knowledge_bases": kbs}), encoding="utf-8")


def _sample_kb(kb_id: str = "azure-waf", **overrides) -> dict:
    base = {
        "id": kb_id,
        "name": "Azure WAF",
        "status": "active",
        "profiles": ["chat", "proposal"],
        "priority": 1,
        "paths": {"index": f"{kb_id}/index", "documents": f"{kb_id}/documents"},
    }
    base.update(overrides)
    return base


@pytest.fixture()
def kb_env(tmp_path: Path):
    """Set up a KBManager backed by tmp_path with one sample KB."""
    config_path = tmp_path / "config.json"
    _write_config(config_path, [_sample_kb()])

    ai_config = AIConfig(
        llm_provider="openai",
        embedding_provider="openai",
        openai_api_key="test-openai-key",
        openai_llm_model="gpt-4o-mini",
        openai_embedding_model="text-embedding-3-small",
    )

    with patch(f"{_MODULE}.get_kb_storage_root", return_value=tmp_path), \
         patch("app.kb.models.get_kb_storage_root", return_value=tmp_path), \
         patch("app.kb.models.AIConfig.default", return_value=ai_config), \
         patch("app.kb.models.get_kb_defaults") as mock_defs:
        mock_defs.return_value.chunk_size = 1024
        mock_defs.return_value.chunk_overlap = 200

        from app.kb.knowledge_base_manager import KBManager

        mgr = KBManager(config_path=str(config_path))
        yield mgr, config_path, tmp_path


class TestListAndGet:
    def test_list_kbs_returns_loaded(self, kb_env):
        mgr, _, _ = kb_env
        items = mgr.list_kbs()
        assert len(items) == 1
        assert items[0]["id"] == "azure-waf"

    def test_get_kb_found(self, kb_env):
        mgr, _, _ = kb_env
        kb = mgr.get_kb("azure-waf")
        assert kb is not None
        assert kb.name == "Azure WAF"

    def test_get_kb_not_found(self, kb_env):
        mgr, _, _ = kb_env
        assert mgr.get_kb("nope") is None

    def test_kb_exists(self, kb_env):
        mgr, _, _ = kb_env
        assert mgr.kb_exists("azure-waf") is True
        assert mgr.kb_exists("nope") is False

    def test_get_active_kbs(self, kb_env):
        mgr, _, _ = kb_env
        active = mgr.get_active_kbs()
        assert len(active) == 1
        assert active[0].id == "azure-waf"

    def test_get_kbs_for_profile(self, kb_env):
        mgr, _, _ = kb_env
        chat_kbs = mgr.get_kbs_for_profile("chat")
        assert len(chat_kbs) == 1
        proposal_kbs = mgr.get_kbs_for_profile("proposal")
        assert len(proposal_kbs) == 1
        unknown_kbs = mgr.get_kbs_for_profile("unknown")
        assert len(unknown_kbs) == 0


class TestCreateKB:
    def test_create_kb(self, kb_env):
        mgr, config_path, tmp_path = kb_env
        new_cfg = _sample_kb("new-kb", name="New KB")
        mgr.create_kb("new-kb", new_cfg)

        assert mgr.kb_exists("new-kb")
        assert (tmp_path / "new-kb" / "index").is_dir()
        assert (tmp_path / "new-kb" / "documents").is_dir()

        # Persisted to config.json
        saved = json.loads(config_path.read_text(encoding="utf-8"))
        ids = [kb["id"] for kb in saved["knowledge_bases"]]
        assert "new-kb" in ids

    def test_create_duplicate_raises(self, kb_env):
        mgr, _, _ = kb_env
        with pytest.raises(ValueError, match="already exists"):
            mgr.create_kb("azure-waf", _sample_kb())


class TestUpdateKB:
    def test_update_kb(self, kb_env):
        mgr, config_path, _ = kb_env
        updated_cfg = _sample_kb(name="Updated WAF", priority=10)
        mgr.update_kb_config("azure-waf", updated_cfg)

        kb = mgr.get_kb("azure-waf")
        assert kb is not None
        assert kb.name == "Updated WAF"
        assert kb.priority == 10

    def test_update_nonexistent_raises(self, kb_env):
        mgr, _, _ = kb_env
        with pytest.raises(ValueError, match="not found"):
            mgr.update_kb_config("nope", {})


class TestDeleteKB:
    def test_delete_kb_removes_from_config(self, kb_env):
        mgr, config_path, tmp_path = kb_env
        # Create dir to verify deletion
        kb_dir = tmp_path / "azure-waf"
        kb_dir.mkdir(parents=True, exist_ok=True)

        mgr.delete_kb("azure-waf")
        assert not kb_dir.exists()

        saved = json.loads(config_path.read_text(encoding="utf-8"))
        assert len(saved["knowledge_bases"]) == 0

    def test_delete_nonexistent_raises(self, kb_env):
        mgr, _, _ = kb_env
        with pytest.raises(ValueError, match="not found"):
            mgr.delete_kb("nope")


class TestEdgeCases:
    def test_missing_config_file(self, tmp_path):
        """KBManager with non-existent config → empty knowledge_bases."""
        ai_config = AIConfig(
            llm_provider="openai",
            embedding_provider="openai",
            openai_api_key="test-openai-key",
            openai_llm_model="gpt-4o-mini",
            openai_embedding_model="text-embedding-3-small",
        )

        with patch(f"{_MODULE}.get_kb_storage_root", return_value=tmp_path), \
             patch("app.kb.models.get_kb_storage_root", return_value=tmp_path), \
             patch("app.kb.models.AIConfig.default", return_value=ai_config), \
             patch("app.kb.models.get_kb_defaults") as mock_defs:
            mock_defs.return_value.chunk_size = 1024
            mock_defs.return_value.chunk_overlap = 200

            from app.kb.knowledge_base_manager import KBManager

            mgr = KBManager(config_path=str(tmp_path / "missing.json"))
            assert mgr.list_kbs() == []

    def test_inactive_kb_excluded_from_active(self, kb_env):
        mgr, config_path, tmp_path = kb_env
        # Add an inactive KB
        saved = json.loads(config_path.read_text(encoding="utf-8"))
        saved["knowledge_bases"].append(
            _sample_kb("inactive-kb", name="Inactive", status="disabled")
        )
        config_path.write_text(json.dumps(saved), encoding="utf-8")
        mgr._load_config()

        assert mgr.kb_exists("inactive-kb")
        active = mgr.get_active_kbs()
        assert all(kb.id != "inactive-kb" for kb in active)
