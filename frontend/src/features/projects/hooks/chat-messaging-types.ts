import type { Dispatch, SetStateAction } from "react";
import type { Message } from "../../../types/api";

export interface UseChatMessagingProps {
  readonly projectId: string | null;
  readonly messages: readonly Message[];
  readonly setMessages: Dispatch<SetStateAction<readonly Message[]>>;
  readonly setLoading: (loading: boolean) => void;
  readonly setLoadingMessage: (msg: string) => void;
}

export interface FailedMessage {
  readonly id: string;
  readonly content: string;
  readonly error: string;
}
