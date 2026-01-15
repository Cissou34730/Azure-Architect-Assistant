import { useContext } from "react";
import { projectContextInstance } from "./ProjectContextInstance";

export function useProjectContext() {
  const context = useContext(projectContextInstance);
  if (context === null) {
    throw new Error("useProjectContext must be used within a ProjectProvider");
  }
  return context;
}
