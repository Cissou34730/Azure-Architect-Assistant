import type { ProjectWorkspaceShellSection } from "../workspaceDefinition";

export const projectWorkspaceShellContributorId = "projects-shell";

export const projectWorkspaceShellSections: readonly ProjectWorkspaceShellSection[] = [
  { id: "project-header", slot: "header" },
  {
    id: "project-tree",
    slot: "left-sidebar",
    collapsedTitle: "Show inputs & artifacts",
    minWidth: 260,
    maxWidth: 480,
    className: "bg-muted",
  },
  {
    id: "workspace-tabs",
    slot: "center",
    className: "flex-1 overflow-hidden px-4 py-4 bg-card panel-scroll-scope",
  },
  {
    id: "project-chat",
    slot: "right-sidebar",
    collapsedTitle: "Show chat",
    minWidth: 280,
    maxWidth: 520,
    className: "bg-muted",
  },
];