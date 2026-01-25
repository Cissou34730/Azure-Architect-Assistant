import { ProjectTab } from "../types";
import ProjectWorkspacePage from "../../pages/ProjectWorkspacePage";

export const workspaceTab: ProjectTab = {
  id: "workspace",
  label: "Workspace",
  path: "workspace",
  component: ProjectWorkspacePage,
};
