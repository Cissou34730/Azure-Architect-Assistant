from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class RuntimeAISelection(BaseModel):
    """Persisted runtime override for the active LLM provider/model."""

    llm_provider: Literal["openai", "azure", "copilot"]
    model_id: str = Field(min_length=1)


def load_runtime_ai_selection(path: Path) -> RuntimeAISelection | None:
    """Return the persisted runtime override when present and valid."""
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return RuntimeAISelection.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Ignoring invalid runtime AI selection at %s: %s", path, exc)
        return None


def persist_runtime_ai_selection(
    path: Path,
    *,
    llm_provider: Literal["openai", "azure", "copilot"],
    model_id: str,
) -> None:
    """Persist the selected provider/model atomically under DATA_ROOT."""
    record = RuntimeAISelection(llm_provider=llm_provider, model_id=model_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    temp_path.replace(path)
