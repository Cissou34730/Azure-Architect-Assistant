"""Cross-feature contract for knowledge-base context."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeContextContract(BaseModel):
    """Knowledge-base context exposed across feature boundaries."""

    model_config = ConfigDict(populate_by_name=True)

    kb_id: str = Field(alias="kbId")
    name: str
    document_count: int = Field(alias="documentCount")
    status: str
