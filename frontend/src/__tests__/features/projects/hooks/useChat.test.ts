import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useChat } from "../../../../features/projects/hooks/useChat";
import type { Message, SendMessageResponse } from "../../../../types/api";

const mockFetchMessages = vi.fn().mockResolvedValue(undefined);
const mockFetchOlderMessages = vi.fn().mockResolvedValue([]);
const mockSendMessage = vi.fn().mockResolvedValue({} as SendMessageResponse);
const mockRetrySendMessage = vi.fn().mockResolvedValue(undefined);

vi.mock("../../../../features/projects/hooks/useChatMessaging", () => ({
  useChatMessaging: vi.fn(() => ({
    fetchMessages: mockFetchMessages,
    fetchOlderMessages: mockFetchOlderMessages,
    sendMessage: mockSendMessage,
    failedMessages: [],
    retrySendMessage: mockRetrySendMessage,
  })),
}));

vi.mock("../../../../features/projects/utils/messageArchive", () => ({
  archiveOldMessages: vi.fn((_id: string, msgs: readonly Message[]) => msgs),
}));

describe("useChat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts with empty state", () => {
    const { result } = renderHook(() => useChat(null));
    expect(result.current.messages).toEqual([]);
    expect(result.current.chatInput).toBe("");
    expect(result.current.loading).toBe(false);
    expect(result.current.loadingMessage).toBe("");
  });

  it("calls fetchMessages on mount", async () => {
    renderHook(() => useChat("p1"));
    await act(async () => {});
    expect(mockFetchMessages).toHaveBeenCalled();
  });

  it("exposes setChatInput for input control", () => {
    const { result } = renderHook(() => useChat("p1"));

    act(() => {
      result.current.setChatInput("hello");
    });

    expect(result.current.chatInput).toBe("hello");
  });

  it("exposes sendMessage from messaging hook", () => {
    const { result } = renderHook(() => useChat("p1"));
    expect(result.current.sendMessage).toBe(mockSendMessage);
  });

  it("exposes refreshMessages as fetchMessages", () => {
    const { result } = renderHook(() => useChat("p1"));
    expect(result.current.refreshMessages).toBe(mockFetchMessages);
  });

  it("exposes fetchOlderMessages", () => {
    const { result } = renderHook(() => useChat("p1"));
    expect(result.current.fetchOlderMessages).toBe(mockFetchOlderMessages);
  });

  it("exposes failedMessages and retrySendMessage", () => {
    const { result } = renderHook(() => useChat("p1"));
    expect(result.current.failedMessages).toEqual([]);
    expect(result.current.retrySendMessage).toBe(mockRetrySendMessage);
  });
});
