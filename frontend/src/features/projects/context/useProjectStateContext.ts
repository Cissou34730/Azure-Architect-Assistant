import { useContext } from "react";
import { ProjectStateContext } from "./ProjectStateContext";

export function useProjectStateContext() {
  const context = useContext(ProjectStateContext);
  if (context === null) {
    throw new Error("useProjectStateContext must be used within ProjectStateProvider");
  }
  return context;
}
