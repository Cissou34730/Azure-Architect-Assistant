import { useContext } from "react";
import { projectMetaContext } from "./ProjectMetaContext";

export function useProjectMetaContext() {
  const context = useContext(projectMetaContext);
  if (context === null) {
    throw new Error(
      "useProjectMetaContext must be used within ProjectMetaProvider",
    );
  }
  return context;
}
