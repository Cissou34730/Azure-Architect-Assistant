import { lazy } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { Layout } from "./Layout";
import { getTabs } from "../features/projects/tabs";

// eslint-disable-next-line @typescript-eslint/naming-convention
const ProjectsPage = lazy(
  () => import("../features/projects/pages/ProjectsPage"),
);
// eslint-disable-next-line @typescript-eslint/naming-convention
const ProjectDetailPage = lazy(
  () => import("../features/projects/pages/ProjectDetailPage"),
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

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Navigate to="/projects" replace />,
      },
      {
        path: "projects",
        element: <ProjectsPage />,
      },
      {
        path: "projects/:projectId",
        element: <ProjectDetailPage />,
        children: [
          {
            index: true,
            element: <Navigate to="documents" replace />,
          },
          ...getTabs().map((tab) => ({
            path: tab.path,
            element: <tab.component />,
          })),
        ],
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
