import { lazy } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { Layout } from "./Layout";
import { LegacyProjectAliasRedirect } from "./LegacyProjectAliasRedirect";

// eslint-disable-next-line @typescript-eslint/naming-convention
const ProjectsPage = lazy(
  () => import("../features/projects/pages/ProjectsPage"),
);
// eslint-disable-next-line @typescript-eslint/naming-convention
const ProjectDetailPage = lazy(
  () => import("../features/projects/pages/ProjectDetailPage"),
);
// eslint-disable-next-line @typescript-eslint/naming-convention
const UnifiedProjectPage = lazy(
  () => import("../features/projects/pages/UnifiedProjectPage"),
);
// eslint-disable-next-line @typescript-eslint/naming-convention
const KBWorkspace = lazy(() =>
  import("../components/kb").then((m) => ({ default: m.KBWorkspace })),
);
// eslint-disable-next-line @typescript-eslint/naming-convention
const IngestionWorkspace = lazy(() =>
  import("../components/ingestion/IngestionWorkspace").then((m) => ({
    default: m.IngestionWorkspace,
  })),
);

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
        path: "project",
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
        path: "kb",
        element: <KBWorkspace />,
      },
      {
        path: "kb-management",
        element: <IngestionWorkspace />,
      },
    ],
  },
]);
