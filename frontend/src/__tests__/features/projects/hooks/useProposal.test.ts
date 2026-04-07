import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useProposal } from "../../../../features/projects/hooks/useProposal";

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

let capturedCallbacks: {
  onProgress: (params: { stage: string }) => void;
  onComplete: (proposal: string) => void;
  onError: (error: string) => void;
};

const mockClose = vi.fn();

vi.mock("../../../../services/proposalService", () => ({
  proposalApi: {
    createProposalStream: vi.fn(
      (
        _projectId: string,
        cbs: {
          onProgress: (params: { stage: string }) => void;
          onComplete: (proposal: string) => void;
          onError: (error: string) => void;
        },
      ) => {
        capturedCallbacks = cbs;
        return { close: mockClose } as unknown as EventSource;
      },
    ),
  },
}));

describe("useProposal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts with empty state", () => {
    const { result } = renderHook(() => useProposal());
    expect(result.current.architectureProposal).toBe("");
    expect(result.current.proposalStage).toBe("");
    expect(result.current.loading).toBe(false);
  });

  it("generateProposal sets loading and stage", () => {
    const { result } = renderHook(() => useProposal());

    act(() => {
      result.current.generateProposal("p1");
    });

    expect(result.current.loading).toBe(true);
    expect(result.current.proposalStage).toBe("Starting proposal generation...");
  });

  it("onProgress updates the stage", () => {
    const { result } = renderHook(() => useProposal());

    act(() => {
      result.current.generateProposal("p1");
    });

    act(() => {
      capturedCallbacks.onProgress({ stage: "Analyzing..." });
    });

    expect(result.current.proposalStage).toBe("Analyzing...");
  });

  it("onComplete sets proposal and resets loading", () => {
    const onComplete = vi.fn();
    const { result } = renderHook(() => useProposal());

    act(() => {
      result.current.generateProposal("p1", onComplete);
    });

    act(() => {
      capturedCallbacks.onComplete("# Architecture Proposal");
    });

    expect(result.current.architectureProposal).toBe("# Architecture Proposal");
    expect(result.current.loading).toBe(false);
    expect(result.current.proposalStage).toBe("");
    expect(onComplete).toHaveBeenCalled();
  });

  it("onError shows toast and resets loading", () => {
    const { result } = renderHook(() => useProposal());

    act(() => {
      result.current.generateProposal("p1");
    });

    act(() => {
      capturedCallbacks.onError("Something went wrong");
    });

    expect(mockShowError).toHaveBeenCalledWith("Something went wrong");
    expect(result.current.loading).toBe(false);
    expect(result.current.proposalStage).toBe("");
  });

  it("closes previous event source on new call", () => {
    const { result } = renderHook(() => useProposal());

    act(() => {
      result.current.generateProposal("p1");
    });

    act(() => {
      result.current.generateProposal("p2");
    });

    // mockClose should have been called for the previous event source
    expect(mockClose).toHaveBeenCalled();
  });
});

