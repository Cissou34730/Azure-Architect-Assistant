"""
Manages WAF checklist templates cached from Microsoft Learn.
"""

import json
import logging
from pathlib import Path

from app.core.app_settings import AppSettings
from app.models.checklist import ChecklistTemplate

logger = logging.getLogger(__name__)


class ChecklistRegistry:
    """
    Manages WAF checklist templates cached from Microsoft Learn.

    Templates are fetched once via MCP server and cached locally.
    No per-project fetches - registry serves from local cache.
    """

    def __init__(self, cache_dir: Path, settings: AppSettings) -> None:
        """
        Initialize the registry.

        Args:
            cache_dir: Local directory for cached WAF template files.
            settings: Main application settings.
        """
        self.cache_dir = cache_dir
        self.settings = settings
        self._templates: dict[str, ChecklistTemplate] = {}
        self._load_cached_templates()

    def _load_cached_templates(self) -> None:
        """
        Scan cache_dir for JSON files and populate the registry.
        """
        if not self.cache_dir.exists():
            logger.warning(f"Cache directory {self.cache_dir} does not exist. Creating it.")
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            return

        loaded_count = 0
        for json_file in self.cache_dir.glob("*.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)

                # Basic validation
                required = ["slug", "title", "version", "content"]
                missing = [f for f in required if f not in data]
                if missing:
                    logger.error(f"Template {json_file} is missing required fields: {missing}")
                    continue

                template = ChecklistTemplate(
                    slug=data["slug"],
                    title=data["title"],
                    description=data.get("description"),
                    version=data["version"],
                    source=data.get("source", "microsoft-learn"),
                    source_url=data.get("source_url", ""),
                    source_version=data.get("source_version", ""),
                    content=data["content"]
                )
                self._templates[template.slug] = template
                loaded_count += 1
            except Exception as e:
                logger.error(f"Failed to load template {json_file}: {e}")

        logger.info(f"Loaded {loaded_count} WAF templates from cache.")

    def get_template(self, slug: str) -> ChecklistTemplate | None:
        """
        Retrieve a template by its slug.

        Args:
            slug: The template slug (e.g., 'waf-2024').

        Returns:
            The template if found, else None.
        """
        template = self._templates.get(slug)
        if not template:
            logger.warning(f"WAF Template not found in registry: {slug}")
        return template

    def list_templates(self) -> list[ChecklistTemplate]:
        """
        List all available templates.

        Returns:
            Sorted list of templates.
        """
        return sorted(self._templates.values(), key=lambda t: t.slug)

    def register_template(self, template: ChecklistTemplate) -> None:
        """
        Register and persist a new template.

        Args:
            template: The template model instance.
        """
        self._templates[template.slug] = template

        # Persist to disk
        file_path = self.cache_dir / f"{template.slug}.json"
        try:
            template_data = {
                "slug": template.slug,
                "title": template.title,
                "description": template.description,
                "version": template.version,
                "source": template.source,
                "source_url": template.source_url,
                "source_version": template.source_version,
                "content": template.content
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(template_data, f, indent=2)
            logger.info(f"Template {template.slug} registered and saved to {file_path}.")
        except Exception as e:
            logger.error(f"Failed to persist template {template.slug} to disk: {e}")

    def refresh_from_cache(self) -> int:
        """
        Refresh the registry from the cache directory.

        Returns:
            Number of templates loaded.
        """
        self._templates.clear()
        self._load_cached_templates()
        return len(self._templates)

