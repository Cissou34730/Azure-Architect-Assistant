import { createContext } from "react";
import type { Project } from "../../../types/api";

interface ProjectMetaContextType {
  readonly selectedProject: Project | null;
  readonly setSelectedProject: (p: Project | null) => void;
  readonly loadingProject: boolean;
}

export const projectMetaContext = createContext<ProjectMetaContextType | null>(
  null
);
