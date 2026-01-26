import { useContext } from "react";
import { ProjectChatContext } from "./ProjectChatContext";

export function useProjectChatContext() {
  const context = useContext(ProjectChatContext);
  if (context === null) {
    throw new Error("useProjectChatContext must be used within ProjectChatProvider");
  }
  return context;
}
