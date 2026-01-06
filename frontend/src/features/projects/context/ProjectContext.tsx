import { createContext, useContext } from "react";
import { useProjectDetails } from "../hooks/useProjectDetails";

type ProjectContextType = ReturnType<typeof useProjectDetails>;

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
