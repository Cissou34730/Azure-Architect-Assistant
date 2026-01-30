import { createContext } from "react";
import type { ProjectState } from "../../../types/api";

interface ProjectStateContextType {
  readonly projectState: ProjectState | null;
  readonly loading: boolean;
  readonly refreshState: () => Promise<void>;
  readonly analyzeDocuments: () => Promise<ProjectState>;
}

export const projectStateContext = createContext<ProjectStateContextType | null>(
  null
);
