"""Cross-feature contract for project conversation state."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ConversationSummaryContract(BaseModel):
    """Conversation summary exposed to other features."""

    model_config = ConfigDict(populate_by_name=True)

    message_count: int = Field(alias="messageCount")
    thread_count: int = Field(alias="threadCount")
    last_message_at: str | None = Field(default=None, alias="lastMessageAt")
