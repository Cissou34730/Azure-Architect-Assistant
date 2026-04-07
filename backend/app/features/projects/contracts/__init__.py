"""Projects feature contracts."""

from .project_summary import ProjectSummaryContract
from .workspace import (
    AgentWorkspaceSummary,
    ProjectWorkspaceArtifacts,
    ProjectWorkspaceChecklistSummary,
    ProjectWorkspaceDiagramSummary,
    ProjectWorkspaceDocuments,
    ProjectWorkspaceInputs,
    ProjectWorkspaceKnowledgeBaseSummary,
    ProjectWorkspaceProjectSummary,
    ProjectWorkspaceSettingsSummary,
    ProjectWorkspaceStateSummary,
    ProjectWorkspaceView,
    workspace_view_to_project_state,
)

__all__ = [
    "AgentWorkspaceSummary",
    "ProjectSummaryContract",
    "ProjectWorkspaceArtifacts",
    "ProjectWorkspaceChecklistSummary",
    "ProjectWorkspaceDiagramSummary",
    "ProjectWorkspaceDocuments",
    "ProjectWorkspaceInputs",
    "ProjectWorkspaceKnowledgeBaseSummary",
    "ProjectWorkspaceProjectSummary",
    "ProjectWorkspaceSettingsSummary",
    "ProjectWorkspaceStateSummary",
    "ProjectWorkspaceView",
    "workspace_view_to_project_state",
]
