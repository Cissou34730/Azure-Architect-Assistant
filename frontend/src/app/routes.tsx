import { lazy } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { Layout } from "./Layout";

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
// eslint-disable-next-line @typescript-eslint/naming-convention
const AgentChatWorkspace = lazy(() =>
  import("../components/agent").then((m) => ({
    default: m.AgentChatWorkspace,
  })),
);

// Legacy tab pages - kept for reference but not in active routes
// eslint-disable-next-line @typescript-eslint/naming-convention
const ProjectOverviewPage = lazy(
  () => import("../features/projects/pages/ProjectOverviewPage"),
);
// eslint-disable-next-line @typescript-eslint/naming-convention
const ProjectDeliverablesPage = lazy(
  () => import("../features/projects/pages/ProjectDeliverablesPage"),
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
          // Legacy tab routes - kept for backward compatibility and reference
          // Users can still navigate to /project/:id/overview or /project/:id/deliverables
          {
            path: "overview",
            element: <ProjectOverviewPage />,
          },
          {
            path: "deliverables",
            element: <ProjectDeliverablesPage />,
          },
          {
            path: "workspace",
            element: <Navigate to=".." replace />,
          },
          {
            path: "documents",
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
        element: <Navigate to="/project/:projectId" replace />,
      },
      {
        path: "kb",
        element: <KBWorkspace />,
      },
      {
        path: "kb-management",
        element: <IngestionWorkspace />,
      },
      {
        path: "agent-chat",
        element: <AgentChatWorkspace />,
      },
    ],
  },
]);
