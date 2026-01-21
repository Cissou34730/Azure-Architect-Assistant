"""
Dynamic prompt loader for Azure Architect Assistant.
Loads prompts from YAML files for easy editing without code changes.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class PromptLoader:
    """
    Load and cache agent prompts from external YAML files.
    Supports hot-reload for dynamic prompt updates.
    """

    _instance: "PromptLoader | None" = None

    @classmethod
    def get_instance(cls) -> "PromptLoader":
        """Get or create the global singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, prompts_dir: Path | str | None = None):
        """
        Initialize prompt loader.

        Args:
            prompts_dir: Directory containing prompt YAML files.
                        Defaults to backend/config/prompts/
        """
        if prompts_dir is None:
            # Default to config/prompts relative to backend root
            # This file is in: backend/app/agents_system/config/prompt_loader.py
            # We need to go up to backend root: ../../../config/prompts
            backend_root = Path(__file__).parent.parent.parent.parent
            prompts_dir = backend_root / "config" / "prompts"

        self.prompts_dir = Path(prompts_dir)
        self._cache: dict[str, Any] = {}
        self._file_path = self.prompts_dir / "agent_prompts.yaml"

        logger.info(f"PromptLoader initialized with directory: {self.prompts_dir}")

    def load_prompts(self, force_reload: bool = False) -> dict[str, Any]:
        """
        Load prompts from YAML file.

        Args:
            force_reload: If True, bypass cache and reload from file

        Returns:
            Dictionary of prompts

        Raises:
            FileNotFoundError: If prompts file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        if self._cache and not force_reload:
            logger.debug("Using cached prompts")
            return self._cache

        if not self._file_path.exists():
            raise FileNotFoundError(
                f"Prompts file not found: {self._file_path}. "
                f"Please create it or check the prompts_dir path."
            )

        try:
            logger.info(f"Loading prompts from {self._file_path}")
            with open(self._file_path, encoding="utf-8") as f:
                prompts = yaml.safe_load(f)

            if not prompts:
                raise ValueError(f"Empty or invalid prompts file: {self._file_path}")

            self._cache = prompts
            logger.info(
                f"Successfully loaded prompts (version: {prompts.get('version', 'unknown')})"
            )
            return prompts

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse prompts YAML: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading prompts: {e}")
            raise

    def get_system_prompt(self) -> str:
        """Get the system prompt."""
        prompts = self.load_prompts()
        return prompts.get("system_prompt", "")

    def get_react_template(self) -> str:
        """Get the ReAct template."""
        prompts = self.load_prompts()
        return prompts.get("react_template", "")

    def get_clarification_prompt(self) -> str:
        """Get the clarification prompt template."""
        prompts = self.load_prompts()
        return prompts.get("clarification_prompt", "")

    def get_conflict_resolution_prompt(self) -> str:
        """Get the conflict resolution prompt template."""
        prompts = self.load_prompts()
        return prompts.get("conflict_resolution_prompt", "")

    def get_few_shot_examples(self) -> list[dict[str, str]]:
        """Get few-shot examples."""
        prompts = self.load_prompts()
        return prompts.get("few_shot_examples", [])

    def reload(self) -> None:
        """Force reload prompts from file."""
        logger.info("Forcing prompt reload...")
        self.load_prompts(force_reload=True)
        logger.info("Prompts reloaded successfully")


def get_prompt_loader() -> PromptLoader:
    """Get or create the global prompt loader instance."""
    return PromptLoader.get_instance()


# Convenience functions for backward compatibility
def get_system_prompt() -> str:
    """Get system prompt from YAML file."""
    return get_prompt_loader().get_system_prompt()


def get_react_template() -> str:
    """Get ReAct template from YAML file."""
    return get_prompt_loader().get_react_template()


def get_clarification_prompt() -> str:
    """Get clarification prompt from YAML file."""
    return get_prompt_loader().get_clarification_prompt()


def get_conflict_resolution_prompt() -> str:
    """Get conflict resolution prompt from YAML file."""
    return get_prompt_loader().get_conflict_resolution_prompt()


def reload_prompts() -> None:
    """Force reload all prompts from file."""
    get_prompt_loader().reload()

