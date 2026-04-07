import { lazy } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { Layout } from "./Layout";
import { LegacyProjectAliasRedirect } from "./LegacyProjectAliasRedirect";
import { workspaceManifestById } from "./workspaceRegistry";

const projectsWorkspaceRoute = workspaceManifestById.projects.route;
const knowledgeWorkspaceRoute = workspaceManifestById.knowledge.route;
const ingestionWorkspaceRoute = workspaceManifestById.ingestion.route;

if (
  projectsWorkspaceRoute === undefined ||
  knowledgeWorkspaceRoute === undefined ||
  ingestionWorkspaceRoute === undefined
) {
  throw new Error("Required workspace route manifests are missing.");
}

function toChildPath(path: string): string {
  return path.startsWith("/") ? path.slice(1) : path;
}

// eslint-disable-next-line @typescript-eslint/naming-convention
const ProjectsPage = lazy(projectsWorkspaceRoute.importRoute);
// eslint-disable-next-line @typescript-eslint/naming-convention
const ProjectDetailPage = lazy(
  () => import("../features/projects/pages/ProjectDetailPage"),
);
// eslint-disable-next-line @typescript-eslint/naming-convention
const UnifiedProjectPage = lazy(
  () => import("../features/projects/pages/UnifiedProjectPage"),
);
// eslint-disable-next-line @typescript-eslint/naming-convention
const KBWorkspace = lazy(knowledgeWorkspaceRoute.importRoute);
// eslint-disable-next-line @typescript-eslint/naming-convention
const IngestionWorkspace = lazy(ingestionWorkspaceRoute.importRoute);

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Navigate to="/project" replace />,
      },
      {
        path: toChildPath(projectsWorkspaceRoute.path),
        element: <ProjectsPage />,
      },
      {
        path: "project/:projectId",
        element: <ProjectDetailPage />,
        children: [
          {
            index: true,
            element: <UnifiedProjectPage />,
          },
          {
            path: "*",
            element: <Navigate to=".." replace />,
          },
        ],
      },
      {
        path: "projects",
        element: <Navigate to="/project" replace />,
      },
      {
        path: "projects/:projectId",
        element: <LegacyProjectAliasRedirect />,
      },
      {
        path: toChildPath(knowledgeWorkspaceRoute.path),
        element: <KBWorkspace />,
      },
      {
        path: toChildPath(ingestionWorkspaceRoute.path),
        element: <IngestionWorkspace />,
      },
    ],
  },
]);

