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
    
    SINGLETON RATIONALE:
    - File I/O caching: YAML prompt files are loaded once and cached in memory
    - Hot-reload capability: Single instance can detect file changes and reload
    - Shared cache: Prompt templates are reused across all agent requests
    - Performance: Avoids repeated file system reads on every agent invocation
    
    Testability:
    - Override via FastAPI dependency injection (see app.dependencies.get_prompt_loader)
    - Use set_instance() to inject mock in unit tests
    - See tests/conftest.py for mock_prompt_loader fixture
    """

    _instance: "PromptLoader | None" = None

    @classmethod
    def get_instance(cls) -> "PromptLoader":
        """Get or create the global singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "PromptLoader | None") -> None:
        """Set or clear singleton instance (for testing/lifecycle)."""
        cls._instance = instance

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
        self._file_cache: dict[str, dict[str, Any]] = {}
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

        prompts = self._load_yaml_file(self._file_path, force_reload=force_reload)
        self._cache = prompts
        logger.info(
            f"Successfully loaded prompts (version: {prompts.get('version', 'unknown')})"
        )
        return prompts

    def load_prompt(self, prompt_name: str, force_reload: bool = False) -> dict[str, Any]:
        """
        Load a specific prompt file or section.

        This method is used by LangGraph specialist nodes that expect prompt files
        such as "architecture_planner_prompt.yaml". It also supports legacy setups
        where prompt sections are nested in the main agent_prompts.yaml file.

        Args:
            prompt_name: Prompt filename (with or without .yaml/.yml), or section key
            force_reload: If True, bypass cache and reload from disk

        Returns:
            Prompt dictionary (typically containing system_prompt and react_template)
        """
        if not prompt_name:
            raise ValueError("prompt_name must be a non-empty string")

        for file_path in self._build_prompt_file_candidates(prompt_name):
            if file_path.exists():
                return self._load_yaml_file(file_path, force_reload=force_reload)

        shared_prompts = self.load_prompts(force_reload=force_reload)
        prompt_section = self._extract_prompt_section(shared_prompts, prompt_name)
        if prompt_section is not None:
            return prompt_section

        raise FileNotFoundError(
            f"Prompt '{prompt_name}' not found in {self.prompts_dir} and no matching "
            "section exists in agent_prompts.yaml."
        )

    def _load_yaml_file(
        self, file_path: Path, force_reload: bool = False
    ) -> dict[str, Any]:
        """Load and cache a YAML file."""
        cache_key = str(file_path.resolve())
        if cache_key in self._file_cache and not force_reload:
            logger.debug(f"Using cached prompt file: {file_path.name}")
            return self._file_cache[cache_key]

        if not file_path.exists():
            raise FileNotFoundError(
                f"Prompts file not found: {file_path}. "
                f"Please create it or check the prompts_dir path."
            )

        try:
            logger.info(f"Loading prompts from {file_path}")
            with open(file_path, encoding="utf-8") as file:
                prompts = yaml.safe_load(file)

            if not isinstance(prompts, dict) or not prompts:
                raise ValueError(f"Empty or invalid prompts file: {file_path}")

            self._file_cache[cache_key] = prompts
            return prompts
        except yaml.YAMLError as exc:
            logger.error(f"Failed to parse prompts YAML: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Unexpected error loading prompts: {exc}")
            raise

    def _build_prompt_file_candidates(self, prompt_name: str) -> list[Path]:
        """Resolve possible file paths for the requested prompt name."""
        base_name = Path(prompt_name).name
        stem = Path(base_name).stem
        suffix = Path(base_name).suffix.lower()

        candidates: list[Path] = []
        if suffix in {".yaml", ".yml"}:
            candidates.append(self.prompts_dir / base_name)
        else:
            candidates.append(self.prompts_dir / f"{base_name}.yaml")
            candidates.append(self.prompts_dir / f"{base_name}.yml")

        # Also support stem-only requests, e.g. "architecture_planner_prompt".
        candidates.append(self.prompts_dir / f"{stem}.yaml")
        candidates.append(self.prompts_dir / f"{stem}.yml")

        deduped: list[Path] = []
        for candidate in candidates:
            if candidate not in deduped:
                deduped.append(candidate)
        return deduped

    def _extract_prompt_section(
        self, prompts: dict[str, Any], prompt_name: str
    ) -> dict[str, Any] | None:
        """Extract prompt section from shared prompts if present."""
        stem = Path(prompt_name).stem
        section_keys = [
            prompt_name,
            stem,
            stem.removesuffix("_prompt"),
            f"{stem}_prompt",
        ]
        for key in section_keys:
            section = prompts.get(key)
            if isinstance(section, dict):
                return section

        if stem in {"agent_prompts", "agent_prompt"} and "system_prompt" in prompts:
            return prompts

        return None

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
        self._cache = {}
        self._file_cache = {}
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

