"""Cross-feature contract for active LLM runtime selection."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RuntimeSelectionContract(BaseModel):
    """Provider/model selection exposed to other features."""

    model_config = ConfigDict(populate_by_name=True)

    provider: str
    model: str
