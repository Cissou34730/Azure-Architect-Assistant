"""
Knowledge Base Manager
Loads and manages multiple knowledge base configurations.
"""

import json
import logging
import os
import shutil
import stat
import time
from pathlib import Path
from typing import Any, cast

from app.core.app_settings import get_kb_storage_root

from .models import KBConfig

logger = logging.getLogger(__name__)


class KBManager:
    """Manages multiple knowledge bases."""

    def __init__(self, config_path: str | None = None) -> None:
        """
        Initialize KB manager.

        Args:
            config_path: Path to config.json. If None, uses default location.
        """
        self.backend_root = Path(__file__).parent.parent.parent
        self.kb_root = Path(get_kb_storage_root())
        self.kb_root_config_value = str(get_kb_storage_root(raw=True))

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
        """Load knowledge base configurations from config.json."""
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
        """Get KB configuration by ID."""
        return self.knowledge_bases.get(kb_id)

    def get_active_kbs(self) -> list[KBConfig]:
        """Get all active knowledge bases."""
        return [kb for kb in self.knowledge_bases.values() if kb.is_active]

    def get_kbs_for_profile(self, profile: str) -> list[KBConfig]:
        """
        Get knowledge bases that support given profile.

        Args:
            profile: 'chat' or 'proposal'

        Returns:
            List of KB configs supporting the profile, sorted by priority
        """
        kbs = [
            kb
            for kb in self.knowledge_bases.values()
            if kb.is_active and kb.supports_profile(profile)
        ]
        # Sort by priority (lower number = higher priority)
        return sorted(kbs, key=lambda kb: kb.priority)

    def list_kbs(self) -> list[dict[str, Any]]:
        """List all knowledge bases with basic info."""
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
        """Check if a KB with given ID exists."""
        return kb_id in self.knowledge_bases

    def get_kb_config(self, kb_id: str) -> dict[str, Any]:
        """Get raw KB configuration dictionary."""
        kb = self.get_kb(kb_id)
        if not kb:
            raise ValueError(f"KB '{kb_id}' not found")

        # Return full config dict
        with open(self.config_path, encoding="utf-8") as f:
            config = json.load(f)

        for kb_dict in config.get("knowledge_bases", []):
            if kb_dict["id"] == kb_id:
                return cast(dict[str, Any], kb_dict)

        raise ValueError(f"KB '{kb_id}' not found in config")

    def get_kb_storage_path(self, kb_id: str) -> str:
        """Get storage directory path for a KB."""
        kb_dir = self.kb_root / kb_id
        return str(kb_dir / "index")

    def create_kb(self, kb_id: str, kb_config: dict[str, Any]) -> None:
        """
        Create a new knowledge base.

        Args:
            kb_id: Unique KB identifier
            kb_config: KB configuration dictionary
        """
        if self.kb_exists(kb_id):
            raise ValueError(f"KB '{kb_id}' already exists")

        # Create KB directory structure
        kb_dir = self.kb_root / kb_id
        kb_dir.mkdir(parents=True, exist_ok=True)
        (kb_dir / "index").mkdir(exist_ok=True)
        (kb_dir / "documents").mkdir(exist_ok=True)

        # Update paths in config
        kb_config["paths"] = {
            # Store paths relative to KNOWLEDGE_BASES_ROOT for portability.
            # These are resolved to absolute paths via get_kb_storage_root().
            "index": f"{kb_id}/index",
            "documents": f"{kb_id}/documents",
        }

        # Add to config.json
        try:
            with open(self.config_path, encoding="utf-8") as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {"knowledge_bases": []}

        config["knowledge_bases"].append(kb_config)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        # Reload config
        self._load_config()

        logger.info(f"Created KB: {kb_id}")

    def update_kb_config(self, kb_id: str, kb_config: dict[str, Any]) -> None:
        """
        Update KB configuration.

        Args:
            kb_id: KB identifier
            kb_config: Updated KB configuration
        """
        if not self.kb_exists(kb_id):
            raise ValueError(f"KB '{kb_id}' not found")

        # Load current config
        with open(self.config_path, encoding="utf-8") as f:
            config = json.load(f)

        # Update KB in list
        for i, kb_dict in enumerate(config["knowledge_bases"]):
            if kb_dict["id"] == kb_id:
                config["knowledge_bases"][i] = kb_config
                break

        # Save config
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        # Reload config
        self._load_config()

        logger.info(f"Updated KB: {kb_id}")

    def delete_kb(self, kb_id: str) -> None:
        """
        Delete a knowledge base and all its data.

        Args:
            kb_id: KB identifier
        """
        if not self.kb_exists(kb_id):
            raise ValueError(f"KB '{kb_id}' not found")

        # Remove from config.json
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

        # Delete KB directory and all its data
        kb_dir = self.kb_root / kb_id

        if kb_dir.exists():
            # Try to delete with retries (handles Windows file locking issues)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # On Windows, use onerror handler to handle permission issues
                    def handle_remove_readonly(func: Any, path: str, exc: Any) -> None:
                        """Handle readonly files on Windows"""
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
                        time.sleep(0.5)  # Wait before retry
                    else:
                        logger.error(
                            f"Failed to delete KB directory after {max_retries} attempts: {e}"
                        )
                        raise ValueError(
                            f"Failed to delete KB data: {e!s}. Files may be in use."
                        ) from e

        # Reload config
        self._load_config()

        logger.info(f"Deleted KB: {kb_id}")

        # Reload config
        self._load_config()

        logger.info(f"Deleted KB: {kb_id}")

