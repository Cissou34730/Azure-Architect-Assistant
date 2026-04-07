import type { WorkspaceManifest } from "../../app/workspaceManifest";

export const knowledgeWorkspaceManifest: WorkspaceManifest = {
  id: "knowledge",
  title: "Knowledge Base",
  summary: "Knowledge base query workspace, hooks, and API client.",
  route: {
    path: "/kb",
    navLabel: "Knowledge Base",
    ariaLabel: "Query knowledge bases",
    importRoute: () =>
      import("./components").then((module) => ({ default: module.KBWorkspace })),
  },
};