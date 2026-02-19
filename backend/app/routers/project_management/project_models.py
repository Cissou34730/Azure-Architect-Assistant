"""
Request/Response Models for Project Management API
"""

from typing import Any

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    """Request to create a new project"""

    name: str


class UpdateRequirementsRequest(BaseModel):
    """Request to update project requirements"""

    text_requirements: str = Field(alias="textRequirements")


class ChatMessageRequest(BaseModel):
    """Request to send a chat message"""

    message: str


class ProjectResponse(BaseModel):
    """Single project response"""

    project: dict[str, Any]


class ProjectsListResponse(BaseModel):
    """List of projects response"""

    projects: list[dict[str, Any]]


class DocumentsResponse(BaseModel):
    """List of documents response"""

    documents: list[dict[str, Any]]
    upload_summary: dict[str, Any] = Field(default_factory=dict, alias="uploadSummary")


class StateResponse(BaseModel):
    """Project state response"""

    project_state: dict[str, Any] = Field(alias="projectState")


class MessagesResponse(BaseModel):
    """Conversation messages response"""

    messages: list[dict[str, Any]]


class ChatResponse(BaseModel):
    """Chat response with updated state"""

    message: str
    project_state: dict[str, Any] = Field(alias="projectState")
    waf_sources: list[dict[str, Any]] = Field(default_factory=list, alias="wafSources")


class BulkDeleteProjectsRequest(BaseModel):
    """Request to bulk delete multiple projects"""

    project_ids: list[str] = Field(alias="projectIds")


class DeleteResponse(BaseModel):
    """Response for delete operations"""

    message: str
    deleted_count: int = Field(default=1, alias="deletedCount")
    project_ids: list[str] = Field(default_factory=list, alias="projectIds")

