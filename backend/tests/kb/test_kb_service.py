"""Unit tests for KnowledgeBaseService with mocked LlamaIndex."""

from unittest.mock import MagicMock, Mock, patch

import pytest

_SVC_MODULE = "app.features.knowledge.infrastructure.service"


def _make_kb_config(**overrides):
    """Create a mock KBConfig with sensible defaults."""
    cfg = Mock()
    cfg.id = overrides.get("id", "test-kb")
    cfg.name = overrides.get("name", "Test KB")
    cfg.index_path = overrides.get("index_path", "/tmp/test-kb/index")
    cfg.embedding_model = overrides.get("embedding_model", "text-embedding-3-small")
    cfg.generation_model = overrides.get("generation_model", "gpt-4o-mini")
    return cfg


class TestKnowledgeBaseService:
    @patch(f"{_SVC_MODULE}._INDEX_CACHE", {})
    @patch(f"{_SVC_MODULE}.load_index_from_storage")
    @patch(f"{_SVC_MODULE}.StorageContext")
    @patch("os.path.exists", return_value=True)
    def test_get_index_loads_and_caches(self, mock_exists, mock_sc, mock_load):
        from app.features.knowledge.infrastructure.service import _INDEX_CACHE, KnowledgeBaseService

        mock_sc_instance = MagicMock()
        mock_sc.from_defaults.return_value = mock_sc_instance
        fake_index = MagicMock()
        mock_load.return_value = fake_index

        cfg = _make_kb_config()
        svc = KnowledgeBaseService(cfg)
        svc._settings_configured = True  # Skip _ensure_settings (requires real AIService)
        index = svc.get_index()

        assert index is fake_index
        assert cfg.index_path in _INDEX_CACHE
        mock_load.assert_called_once_with(mock_sc_instance)

    @patch(f"{_SVC_MODULE}._INDEX_CACHE")
    def test_get_index_returns_cached(self, mock_cache):
        from app.features.knowledge.infrastructure.service import KnowledgeBaseService

        cached_index = MagicMock()
        mock_cache.__contains__ = Mock(return_value=True)
        mock_cache.__getitem__ = Mock(return_value=cached_index)

        cfg = _make_kb_config()
        svc = KnowledgeBaseService(cfg)
        svc._settings_configured = True
        index = svc.get_index()

        assert index is cached_index

    @patch(f"{_SVC_MODULE}._INDEX_CACHE", {})
    @patch("os.path.exists", return_value=False)
    def test_get_index_missing_dir_raises(self, mock_exists):
        from app.features.knowledge.infrastructure.service import KnowledgeBaseService

        cfg = _make_kb_config()
        svc = KnowledgeBaseService(cfg)
        svc._settings_configured = True

        with pytest.raises(FileNotFoundError, match="Index not found"):
            svc.get_index()


class TestIsIndexReady:
    def test_ready_when_docstore_exists(self, tmp_path):
        from app.features.knowledge.infrastructure.service import KnowledgeBaseService

        storage = tmp_path / "index"
        storage.mkdir()
        (storage / "docstore.json").write_text("{}")

        cfg = _make_kb_config(index_path=str(storage))
        svc = KnowledgeBaseService(cfg)
        assert svc.is_index_ready() is True

    def test_not_ready_when_dir_missing(self, tmp_path):
        from app.features.knowledge.infrastructure.service import KnowledgeBaseService

        cfg = _make_kb_config(index_path=str(tmp_path / "nope"))
        svc = KnowledgeBaseService(cfg)
        assert svc.is_index_ready() is False

    def test_not_ready_when_no_docstore(self, tmp_path):
        from app.features.knowledge.infrastructure.service import KnowledgeBaseService

        storage = tmp_path / "index"
        storage.mkdir()

        cfg = _make_kb_config(index_path=str(storage))
        svc = KnowledgeBaseService(cfg)
        assert svc.is_index_ready() is False


class TestCacheHelpers:
    @patch(f"{_SVC_MODULE}._INDEX_CACHE", {"a": MagicMock(), "b": MagicMock()})
    def test_clear_specific(self):
        from app.features.knowledge.infrastructure.service import _INDEX_CACHE, clear_index_cache

        clear_index_cache(kb_id="kb-a", storage_dir="a")
        assert "a" not in _INDEX_CACHE
        assert "b" in _INDEX_CACHE

    @patch(f"{_SVC_MODULE}._INDEX_CACHE", {"a": MagicMock(), "b": MagicMock()})
    def test_clear_all(self):
        from app.features.knowledge.infrastructure.service import _INDEX_CACHE, clear_index_cache

        clear_index_cache()
        assert len(_INDEX_CACHE) == 0

    @patch(f"{_SVC_MODULE}._INDEX_CACHE", {"x": MagicMock()})
    def test_get_cached_count(self):
        from app.features.knowledge.infrastructure.service import get_cached_index_count

        assert get_cached_index_count() == 1
