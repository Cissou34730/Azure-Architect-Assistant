"""KB domain models: configuration and profiles."""

import os
from typing import List
from app.core.config import get_openai_settings, get_kb_defaults


class KBConfig:
    """Knowledge base configuration."""

    def __init__(self, config_dict: dict):
        openai_settings = get_openai_settings()
        kb_defaults = get_kb_defaults()

        self.id: str = config_dict["id"]
        self.name: str = config_dict["name"]
        self.description: str = config_dict.get("description", "")
        self.status: str = config_dict.get("status", "active")
        self.embedding_model: str = config_dict.get(
            "embedding_model", openai_settings.embedding_model
        )
        self.generation_model: str = config_dict.get(
            "generation_model", openai_settings.model
        )
        self.chunk_size: int = config_dict.get("chunk_size", kb_defaults.chunk_size)
        self.chunk_overlap: int = config_dict.get(
            "chunk_overlap", kb_defaults.chunk_overlap
        )
        self.source_url: str = config_dict.get("source_url", "")
        self.paths: dict = config_dict.get("paths", {})
        # Indexed flag: true when index was built
        self.indexed: bool = bool(config_dict.get("indexed", False))

        self.profiles: List[str] = config_dict.get("profiles", ["chat", "proposal"])
        self.priority: int = config_dict.get("priority", 5)

    @property
    def index_path(self) -> str:
        if "index" in self.paths:
            index_path = self.paths["index"]
            if os.path.isabs(index_path):
                return index_path
            from app.core.config import get_kb_storage_root

            kb_root = get_kb_storage_root()
            return str(kb_root / index_path)
        return ""

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    def supports_profile(self, profile: str) -> bool:
        return profile in self.profiles
