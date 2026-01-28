import { createContext } from "react";
import type { Message, SendMessageResponse, ProjectState } from "../../../types/api";

export interface ProjectChatContextType {
  readonly messages: readonly Message[];
  readonly sendMessage: (
    content: string,
    onStateUpdate?: (state: ProjectState) => void
  ) => Promise<SendMessageResponse>;
  readonly loading: boolean;
  readonly loadingMessage: string | null;
  readonly refreshMessages: () => Promise<void>;
}

export const projectChatContext = createContext<ProjectChatContextType | null>(
  null
);
