import { createContext } from "react";
import type { Message } from "../../../types/api";

export interface ProjectChatContextType {
  readonly messages: readonly Message[];
  readonly sendMessage: (content: string) => Promise<void>;
  readonly loading: boolean;
  readonly loadingMessage: string | null;
  readonly refreshMessages: () => Promise<void>;
}

export const ProjectChatContext = createContext<ProjectChatContextType | null>(
  null
);
