import { createContext } from "react";
import type { ProjectContextType } from "./types";

export const projectContextInstance = createContext<ProjectContextType | null>(
  null
);
