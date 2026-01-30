import { useContext } from "react";
import { projectStateContext } from "./ProjectStateContext";

export function useProjectStateContext() {
  const context = useContext(projectStateContext);
  if (context === null) {
    throw new Error(
      "useProjectStateContext must be used within ProjectStateProvider",
    );
  }
  return context;
}
