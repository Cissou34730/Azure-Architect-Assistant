/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext } from "react";
import type { ProjectContextType } from "./types";

const ProjectContext = createContext<ProjectContextType | null>(null);

export function ProjectProvider({
  value,
  children,
}: {
  value: ProjectContextType;
  children: React.ReactNode;
}) {
  return (
    <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>
  );
}

export function useProjectContext() {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error("useProjectContext must be used within a ProjectProvider");
  }
  return context;
}
