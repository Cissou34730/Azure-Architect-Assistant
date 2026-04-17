"""Project notes API contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProjectNoteCategory = Literal["decision", "context", "question", "risk"]


class ProjectNoteContract(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    project_id: str = Field(alias="projectId")
    category: ProjectNoteCategory
    content: str
    source_message_id: str | None = Field(default=None, alias="sourceMessageId")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class ProjectNoteUpsertRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    category: ProjectNoteCategory
    content: str
    source_message_id: str | None = Field(default=None, alias="sourceMessageId")


class ProjectNotesListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    notes: list[ProjectNoteContract]


class ProjectNoteResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    note: ProjectNoteContract


class ProjectNoteDeleteResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    deleted: bool
    note_id: str = Field(alias="noteId")

