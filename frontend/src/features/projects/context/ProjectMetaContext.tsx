import { createContext } from "react";
import type { Project } from "../../../types/api";

export interface ProjectMetaContextType {
  readonly selectedProject: Project | null;
  readonly setSelectedProject: (p: Project | null) => void;
  readonly loadingProject: boolean;
  readonly activeTab: string | null;
  readonly setActiveTab: (tab: string) => void;
}

export const ProjectMetaContext = createContext<ProjectMetaContextType | null>(
  null
);
