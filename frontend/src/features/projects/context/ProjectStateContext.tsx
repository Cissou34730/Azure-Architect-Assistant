import { createContext } from "react";
import type { ProjectState } from "../../../types/api";

export interface ProjectStateContextType {
  readonly projectState: ProjectState | null;
  readonly loading: boolean;
  readonly refreshState: () => Promise<void> | void;
  readonly analyzeDocuments: () => Promise<ProjectState | void>;
}

export const ProjectStateContext = createContext<ProjectStateContextType | null>(
  null
);
