import { createContext } from "react";
import type { Message, SendMessageResponse, ProjectState } from "../../../types/api";
import type { FailedMessage } from "../hooks/useChatMessaging";

export interface ProjectChatContextType {
  readonly messages: readonly Message[];
  readonly sendMessage: (
    content: string,
    onStateUpdate?: (state: ProjectState) => void
  ) => Promise<SendMessageResponse>;
  readonly loading: boolean;
  readonly loadingMessage: string | null;
  readonly refreshMessages: () => Promise<void>;
  readonly fetchOlderMessages: (beforeId: string) => Promise<readonly Message[]>;
  readonly failedMessages: readonly FailedMessage[];
  readonly retrySendMessage: (failedId: string) => Promise<void>;
}

export const projectChatContext = createContext<ProjectChatContextType | null>(
  null
);
