import { useContext } from "react";
import { ProjectMetaContext } from "./ProjectMetaContext";

export function useProjectMetaContext() {
  const context = useContext(ProjectMetaContext);
  if (context === null) {
    throw new Error("useProjectMetaContext must be used within ProjectMetaProvider");
  }
  return context;
}
