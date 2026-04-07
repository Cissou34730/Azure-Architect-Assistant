import type { WorkspaceManifest } from "../../app/workspaceManifest";

export const ingestionWorkspaceManifest: WorkspaceManifest = {
  id: "ingestion",
  title: "KB Management",
  summary: "Knowledge base creation and ingestion management workspace.",
  route: {
    path: "/kb-management",
    navLabel: "KB Management",
    ariaLabel: "Manage knowledge bases",
    importRoute: () =>
      import("./components/IngestionWorkspace").then((module) => ({
        default: module.IngestionWorkspace,
      })),
  },
};