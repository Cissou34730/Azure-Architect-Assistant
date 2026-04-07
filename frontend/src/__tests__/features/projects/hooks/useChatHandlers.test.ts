import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { useChatHandlers } from "../../../../features/projects/hooks/useChatHandlers";
import type { SendMessageResponse } from "../../../../features/knowledge/types/api-kb";

type SendFn = (msg: string) => Promise<SendMessageResponse>;

const mockShowError = vi.fn();

vi.mock("../../../../shared/hooks/useToast", () => ({
  useToast: () => ({
    error: mockShowError,
    success: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
    show: vi.fn(),
    toasts: [],
    close: vi.fn(),
    closeAll: vi.fn(),
  }),
}));

describe("useChatHandlers", () => {
  let mockSendMessage: Mock<SendFn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockSendMessage = vi.fn<SendFn>();
  });

  it("does nothing when chatInput is empty", async () => {
    const { result } = renderHook(() =>
      useChatHandlers({ chatInput: "  ", sendMessage: mockSendMessage }),
    );

    await act(async () => {
      await result.current.handleSendChatMessage();
    });

    expect(mockSendMessage).not.toHaveBeenCalled();
  });

  it("calls sendMessage with chatInput", async () => {
    mockSendMessage.mockResolvedValue({} as SendMessageResponse);
    const { result } = renderHook(() =>
      useChatHandlers({ chatInput: "hello", sendMessage: mockSendMessage }),
    );

    await act(async () => {
      await result.current.handleSendChatMessage();
    });

    expect(mockSendMessage).toHaveBeenCalledWith("hello");
  });

  it("prevents default on event", async () => {
    mockSendMessage.mockResolvedValue({} as SendMessageResponse);
    const preventDefault = vi.fn();
    const { result } = renderHook(() =>
      useChatHandlers({ chatInput: "hi", sendMessage: mockSendMessage }),
    );

    await act(async () => {
      await result.current.handleSendChatMessage({
        preventDefault,
      } as unknown as React.SyntheticEvent);
    });

    expect(preventDefault).toHaveBeenCalled();
  });

  it("shows error toast on sendMessage failure", async () => {
    mockSendMessage.mockRejectedValue(new Error("network"));
    const { result } = renderHook(() =>
      useChatHandlers({ chatInput: "hi", sendMessage: mockSendMessage }),
    );

    await act(async () => {
      await result.current.handleSendChatMessage();
    });

    expect(mockShowError).toHaveBeenCalledWith(expect.stringContaining("network"));
  });

  it("shows generic error for non-Error throws", async () => {
    mockSendMessage.mockRejectedValue("string-error");
    const { result } = renderHook(() =>
      useChatHandlers({ chatInput: "hi", sendMessage: mockSendMessage }),
    );

    await act(async () => {
      await result.current.handleSendChatMessage();
    });

    expect(mockShowError).toHaveBeenCalledWith(expect.stringContaining("Chat failed"));
  });
});

