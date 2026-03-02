import { useContext } from "react";
import { projectInputContext } from "./ProjectInputContext";

export function useProjectInputContext() {
  const context = useContext(projectInputContext);
  if (context === null) {
    throw new Error(
      "useProjectInputContext must be used within a ProjectProvider",
    );
  }
  return context;
}
