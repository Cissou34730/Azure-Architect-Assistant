import { useContext } from "react";
import { projectChatContext } from "./ProjectChatContext";

export function useProjectChatContext() {
  const context = useContext(projectChatContext);
  if (context === null) {
    throw new Error(
      "useProjectChatContext must be used within ProjectChatProvider",
    );
  }
  return context;
}
