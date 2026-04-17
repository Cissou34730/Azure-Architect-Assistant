import { createContext } from "react";
import type { Message, SendMessageResponse } from "../../knowledge/types/api-kb";
import type { ProjectState } from "../types/api-project";
import type { FailedMessage } from "../hooks/useChatMessaging";
import type { ActiveChatReview } from "../types/chat-review";

interface ProjectChatContextType {
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
  readonly activeReview: ActiveChatReview | null;
}

export const projectChatContext = createContext<ProjectChatContextType | null>(
  null
);
