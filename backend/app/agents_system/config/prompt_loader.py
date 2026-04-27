"""
Dynamic prompt loader for Azure Architect Assistant.
Loads prompts from YAML files for easy editing without code changes.
"""

import logging
from copy import deepcopy
from pathlib import Path
from string import Template
from threading import Lock
from typing import Any

import yaml  # type: ignore[import-untyped]

from app.agents_system.memory.token_counter import TokenCounter

logger = logging.getLogger(__name__)

_SHARED_PROMPT_FILES: tuple[str, ...] = (
    "constitution.yaml",
    "base_persona.yaml",
    "architect_briefing.yaml",  # P1: output contract — stage-aware briefing structure
    "tool_strategy.yaml",
    "guardrails.yaml",
)

_AGENT_PROMPT_FILE_MAP: dict[str, str] = {
    "orchestrator": "orchestrator_routing.yaml",
    "architecture_planner": "architecture_planner_prompt.yaml",
    "iac_generator": "iac_generator_prompt.yaml",
    "cost_estimator": "cost_estimator_prompt.yaml",
    "saas_advisor": "saas_advisor_prompt.yaml",
    "requirements_extractor": "requirements_extraction.yaml",
    "clarification_planner": "clarification_planner.yaml",
    "adr_writer": "adr_writer.yaml",
    "waf_validator": "waf_validator.yaml",
    "researcher": "research.yaml",
}

_STAGE_PROMPT_FILE_MAP: dict[str, str] = {
    "extract_requirements": "requirements_extraction.yaml",
    "clarify": "clarification_planner.yaml",
    "manage_adr": "adr_writer.yaml",
    "validate": "waf_validator.yaml",
}


class PromptLoader:
    """
    Load and cache agent prompts from external YAML files.
    Supports explicit hot-reload for dynamic prompt updates.

    SINGLETON RATIONALE:
    - File I/O caching: YAML prompt files are loaded once and cached in memory
    - Hot-reload capability: Single instance can be explicitly reloaded on demand
    - Shared cache: Prompt templates are reused across all agent requests
    - Performance: Avoids repeated file system reads on every agent invocation

    Testability:
    - Override via FastAPI dependency injection (see app.dependencies.get_prompt_loader)
    - Use set_instance() to inject mock in unit tests
    - See tests/conftest.py for mock_prompt_loader fixture
    """

    _instance: "PromptLoader | None" = None
    _instance_lock = Lock()

    @classmethod
    def get_instance(cls) -> "PromptLoader":
        """Get or create the global singleton instance."""
        if cls._instance is None:
            with cls._instance_lock:
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
            backend_root = Path(__file__).parent.parent.parent.parent
            prompts_dir = backend_root / "config" / "prompts"

        self.prompts_dir = Path(prompts_dir)
        self._cache: dict[str, Any] = {}
        self._file_cache: dict[str, dict[str, Any]] = {}
        self._file_path = self.prompts_dir / "agent_prompts.yaml"
        self._token_counter = TokenCounter()

        logger.info("PromptLoader initialized with directory: %s", self.prompts_dir)

    def load_prompts(self, force_reload: bool = False) -> dict[str, Any]:
        """
        Load prompts from YAML file.

        Args:
            force_reload: If True, bypass cache and reload from file

        Returns:
            Dictionary of prompts
        """
        if self._cache and not force_reload:
            logger.debug("Using cached prompts")
            return deepcopy(self._cache)

        prompts = self._load_yaml_file(self._file_path, force_reload=force_reload)
        self._cache = prompts
        logger.info(
            "Successfully loaded prompts (version: %s)",
            prompts.get("version", "unknown"),
        )
        return deepcopy(prompts)

    def load_prompt(self, prompt_name: str, force_reload: bool = False) -> dict[str, Any]:
        """
        Load a specific prompt file or section.

        This method preserves the legacy monolithic-section fallback. Stage workers
        that must remain isolated from the monolith should call ``load_prompt_file``.
        """
        if not prompt_name:
            raise ValueError("prompt_name must be a non-empty string")

        try:
            return self.load_prompt_file(prompt_name, force_reload=force_reload)
        except FileNotFoundError:
            pass

        shared_prompts = self.load_prompts(force_reload=force_reload)
        prompt_section = self._extract_prompt_section(shared_prompts, prompt_name)
        if prompt_section is not None:
            return prompt_section

        raise FileNotFoundError(
            f"Prompt '{prompt_name}' not found in {self.prompts_dir} and no matching "
            "section exists in agent_prompts.yaml."
        )

    def load_prompt_file(self, prompt_name: str, force_reload: bool = False) -> dict[str, Any]:
        """Load a prompt file from disk without falling back to monolithic sections."""
        if not prompt_name:
            raise ValueError("prompt_name must be a non-empty string")

        for file_path in self._build_prompt_file_candidates(prompt_name):
            if file_path.exists():
                return self._load_yaml_file(file_path, force_reload=force_reload)

        raise FileNotFoundError(f"Prompt file '{prompt_name}' not found in {self.prompts_dir}.")

    def _load_yaml_file(
        self, file_path: Path, force_reload: bool = False
    ) -> dict[str, Any]:
        """Load and cache a YAML file."""
        cache_key = str(file_path.resolve())
        if cache_key in self._file_cache and not force_reload:
            logger.debug("Using cached prompt file: %s", file_path.name)
            return deepcopy(self._file_cache[cache_key])

        if not file_path.exists():
            raise FileNotFoundError(
                f"Prompts file not found: {file_path}. "
                f"Please create it or check the prompts_dir path."
            )

        try:
            logger.info("Loading prompts from %s", file_path)
            with open(file_path, encoding="utf-8") as file:
                prompts = yaml.safe_load(file)

            if not isinstance(prompts, dict) or not prompts:
                raise ValueError(f"Empty or invalid prompts file: {file_path}")

            self._file_cache[cache_key] = prompts
            return deepcopy(prompts)
        except yaml.YAMLError as exc:
            logger.error("Failed to parse prompts YAML: %s", exc)
            raise
        except Exception as exc:
            logger.error("Unexpected error loading prompts: %s", exc)
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

    def compose_prompt(
        self,
        agent_type: str,
        stage: str,
        context_budget: int,
        *,
        force_reload: bool = False,
    ) -> str:
        """Compose a modular system prompt with legacy fallback."""
        sections: list[str] = []
        seen_files: set[str] = set()
        substitutions = {
            "agent_type": agent_type,
            "stage": stage,
            "context_budget": str(context_budget),
        }

        prompt_files = self._compose_prompt_files(agent_type=agent_type, stage=stage)
        for prompt_file in prompt_files:
            if not prompt_file or prompt_file in seen_files:
                continue
            seen_files.add(prompt_file)

            prompt_text = self._load_optional_system_prompt_file(
                prompt_file,
                force_reload=force_reload,
            )
            if not prompt_text:
                continue
            rendered = Template(prompt_text).safe_substitute(substitutions).strip()
            if rendered:
                sections.append(rendered)

        composed_prompt = "\n\n".join(sections) if sections else self.get_system_prompt()
        if context_budget <= 0:
            return composed_prompt
        if self._token_counter.fits_within_budget(composed_prompt, context_budget):
            return composed_prompt
        logger.warning(
            "Composed prompt exceeded budget (%d tokens > %d); truncating",
            self._token_counter.count_tokens(composed_prompt),
            context_budget,
        )
        return self._token_counter.truncate_to_budget(composed_prompt, context_budget)

    def _compose_prompt_files(self, *, agent_type: str, stage: str) -> list[str]:
        stage_prompt_file = _STAGE_PROMPT_FILE_MAP.get(stage, "")
        agent_prompt_file = _AGENT_PROMPT_FILE_MAP.get(agent_type, "")
        prompt_files = [_SHARED_PROMPT_FILES[0]]
        if agent_prompt_file and not (agent_type == "orchestrator" and stage_prompt_file):
            prompt_files.append(agent_prompt_file)
        if stage_prompt_file:
            prompt_files.append(stage_prompt_file)
        prompt_files.extend(_SHARED_PROMPT_FILES[1:])
        return prompt_files

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

    def _load_optional_system_prompt_file(
        self,
        prompt_name: str,
        *,
        force_reload: bool = False,
    ) -> str | None:
        try:
            prompt = self.load_prompt_file(prompt_name, force_reload=force_reload)
        except FileNotFoundError:
            return None

        system_prompt = prompt.get("system_prompt")
        if isinstance(system_prompt, str):
            return system_prompt
        return None

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


def get_clarification_prompt() -> str:
    """Get clarification prompt from YAML file."""
    return get_prompt_loader().get_clarification_prompt()


def get_conflict_resolution_prompt() -> str:
    """Get conflict resolution prompt from YAML file."""
    return get_prompt_loader().get_conflict_resolution_prompt()


def reload_prompts() -> None:
    """Force reload all prompts from file."""
    get_prompt_loader().reload()
