import { createBrowserRouter, Navigate } from "react-router-dom";
import { Layout } from "./Layout";
import ProjectsPage from "../features/projects/pages/ProjectsPage";
import ProjectDetailPage from "../features/projects/pages/ProjectDetailPage";
import { KBWorkspace } from "../components/kb";
import { IngestionWorkspace } from "../components/ingestion/IngestionWorkspace";
import { AgentChatWorkspace } from "../components/agent";
import { getTabs } from "../features/projects/tabs";

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
