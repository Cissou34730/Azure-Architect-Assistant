import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useChatMessaging } from "../../../../features/projects/hooks/useChatMessaging";
import type { Message } from "../../../../types/api";
import type { Dispatch, SetStateAction } from "react";

const mockFetchMessages = vi.fn().mockResolvedValue(undefined);
const mockFetchOlderMessages = vi.fn().mockResolvedValue([]);
const mockSendMessage = vi.fn().mockResolvedValue({});
const mockRetrySendMessage = vi.fn().mockResolvedValue(undefined);

vi.mock("../../../../features/projects/hooks/chat-messaging-fetch", () => ({
  useMessagesRef: vi.fn((msgs: readonly Message[]) => ({ current: msgs })),
  useMessageArchiver: vi.fn(),
  useFetchMessages: vi.fn(() => mockFetchMessages),
  useFetchOlderMessages: vi.fn(() => mockFetchOlderMessages),
}));

vi.mock("../../../../features/projects/hooks/chat-messaging-send", () => ({
  useSendMessage: vi.fn(() => mockSendMessage),
  useRetrySendMessage: vi.fn(() => mockRetrySendMessage),
}));

describe("useChatMessaging", () => {
  const setMessages = vi.fn() as unknown as Dispatch<SetStateAction<readonly Message[]>>;
  const setLoading = vi.fn();
  const setLoadingMessage = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns composed hook functions", () => {
    const { result } = renderHook(() =>
      useChatMessaging({
        projectId: "p1",
        messages: [],
        setMessages,
        setLoading,
        setLoadingMessage,
      }),
    );

    expect(result.current.fetchMessages).toBe(mockFetchMessages);
    expect(result.current.fetchOlderMessages).toBe(mockFetchOlderMessages);
    expect(result.current.sendMessage).toBe(mockSendMessage);
    expect(result.current.retrySendMessage).toBe(mockRetrySendMessage);
  });

  it("starts with empty failedMessages", () => {
    const { result } = renderHook(() =>
      useChatMessaging({
        projectId: "p1",
        messages: [],
        setMessages,
        setLoading,
        setLoadingMessage,
      }),
    );

    expect(result.current.failedMessages).toEqual([]);
  });
});
