"""Knowledge Base Manager."""

import json
import logging
import os
import shutil
import stat
import time
from pathlib import Path
from typing import Any, cast

from app.shared.config.app_settings import get_app_settings, get_kb_storage_root

from .models import KBConfig
from .service import KnowledgeBaseService

logger = logging.getLogger(__name__)


class KBManager:
    """Manages multiple knowledge bases."""

    def __init__(self, config_path: str | None = None) -> None:
        self.backend_root = Path(__file__).parent.parent.parent.parent.parent
        self.kb_root = Path(get_kb_storage_root())
        self.kb_root_config_value = str(get_app_settings().knowledge_bases_root)

        if config_path is None:
            resolved_config_path = self.kb_root / "config.json"
        else:
            resolved_config_path = Path(config_path)
            if not resolved_config_path.is_absolute():
                resolved_config_path = self.backend_root / resolved_config_path

        self.config_path = resolved_config_path
        self.knowledge_bases: dict[str, KBConfig] = {}
        self._load_config()

    def _load_config(self) -> None:
        try:
            if not self.config_path.exists():
                logger.warning(f"Config file not found: {self.config_path}")
                return

            with open(self.config_path, encoding="utf-8") as f:
                config = json.load(f)

            for kb_dict in config.get("knowledge_bases", []):
                kb = KBConfig(kb_dict)
                self.knowledge_bases[kb.id] = kb
                logger.info(f"Loaded KB: {kb.id} ({kb.name}) - Status: {kb.status}")

        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to load KB config: {e}")

    def get_kb(self, kb_id: str) -> KBConfig | None:
        return self.knowledge_bases.get(kb_id)

    def get_active_kbs(self) -> list[KBConfig]:
        return [kb for kb in self.knowledge_bases.values() if kb.is_active]

    def get_kbs_for_profile(self, profile: str) -> list[KBConfig]:
        kbs = [
            kb
            for kb in self.knowledge_bases.values()
            if kb.is_active and kb.supports_profile(profile)
        ]
        return sorted(kbs, key=lambda kb: kb.priority)

    def list_kbs(self) -> list[dict[str, Any]]:
        return [
            {
                "id": kb.id,
                "name": kb.name,
                "status": kb.status,
                "profiles": kb.profiles,
                "priority": kb.priority,
            }
            for kb in self.knowledge_bases.values()
        ]

    def kb_exists(self, kb_id: str) -> bool:
        return kb_id in self.knowledge_bases

    def get_kb_config(self, kb_id: str) -> dict[str, Any]:
        kb = self.get_kb(kb_id)
        if not kb:
            raise ValueError(f"KB '{kb_id}' not found")

        with open(self.config_path, encoding="utf-8") as f:
            config = json.load(f)

        for kb_dict in config.get("knowledge_bases", []):
            if kb_dict["id"] == kb_id:
                return cast(dict[str, Any], kb_dict)

        raise ValueError(f"KB '{kb_id}' not found in config")

    def get_kb_storage_path(self, kb_id: str) -> str:
        kb_dir = self.kb_root / kb_id
        return str(kb_dir / "index")

    def create_kb(self, kb_id: str, kb_config: dict[str, Any]) -> None:
        if self.kb_exists(kb_id):
            raise ValueError(f"KB '{kb_id}' already exists")

        kb_dir = self.kb_root / kb_id
        kb_dir.mkdir(parents=True, exist_ok=True)
        (kb_dir / "index").mkdir(exist_ok=True)
        (kb_dir / "documents").mkdir(exist_ok=True)

        kb_config["paths"] = {
            "index": f"{kb_id}/index",
            "documents": f"{kb_id}/documents",
        }

        try:
            with open(self.config_path, encoding="utf-8") as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {"knowledge_bases": []}

        config["knowledge_bases"].append(kb_config)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        self._load_config()
        logger.info(f"Created KB: {kb_id}")

    def update_kb_config(self, kb_id: str, kb_config: dict[str, Any]) -> None:
        if not self.kb_exists(kb_id):
            raise ValueError(f"KB '{kb_id}' not found")

        with open(self.config_path, encoding="utf-8") as f:
            config = json.load(f)

        for i, kb_dict in enumerate(config["knowledge_bases"]):
            if kb_dict["id"] == kb_id:
                config["knowledge_bases"][i] = kb_config
                break

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        self._load_config()
        logger.info(f"Updated KB: {kb_id}")

    def delete_kb(self, kb_id: str) -> None:
        if not self.kb_exists(kb_id):
            raise ValueError(f"KB '{kb_id}' not found")

        try:
            with open(self.config_path, encoding="utf-8") as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {"knowledge_bases": []}

        config["knowledge_bases"] = [
            kb for kb in config["knowledge_bases"] if kb["id"] != kb_id
        ]

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        kb_dir = self.kb_root / kb_id
        if kb_dir.exists():
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    def handle_remove_readonly(func: Any, path: str, exc: Any) -> None:
                        os.chmod(path, stat.S_IWRITE)
                        func(path)

                    shutil.rmtree(kb_dir, onerror=handle_remove_readonly)
                    logger.info(f"Deleted KB directory: {kb_dir}")
                    break
                except PermissionError as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed to delete {kb_dir}: {e}. Retrying..."
                        )
                        time.sleep(0.5)
                    else:
                        logger.error(
                            f"Failed to delete KB directory after {max_retries} attempts: {e}"
                        )
                        raise ValueError(
                            f"Failed to delete KB data: {e!s}. Files may be in use."
                        ) from e

        self._load_config()
        logger.info(f"Deleted KB: {kb_id}")

    def preload_all_indices(self) -> dict[str, float]:
        """Preload indices for all active knowledge bases at startup."""
        timing: dict[str, float] = {}
        active_kbs = self.get_active_kbs()

        if not active_kbs:
            logger.info("No active KBs to preload")
            return timing

        logger.info(f"Preloading {len(active_kbs)} active KB indices...")

        for kb_config in active_kbs:
            try:
                start = time.perf_counter()
                service = KnowledgeBaseService(kb_config)
                service.get_index()
                elapsed = time.perf_counter() - start
                timing[kb_config.id] = elapsed
                logger.info(f"  [ok] [{kb_config.id}] Loaded in {elapsed:.2f}s")
            except Exception as e:  # noqa: BLE001
                logger.error(f"  [fail] [{kb_config.id}] Failed to load: {e}")
                timing[kb_config.id] = -1.0

        total_time = sum(t for t in timing.values() if t > 0)
        success_count = sum(1 for t in timing.values() if t > 0)
        logger.info(
            f"Preloaded {success_count}/{len(active_kbs)} indices in {total_time:.2f}s total"
        )

        return timing
