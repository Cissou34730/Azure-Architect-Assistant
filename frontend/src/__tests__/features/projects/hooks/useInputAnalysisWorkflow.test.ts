import { renderHook, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { useInputAnalysisWorkflow } from "../../../../features/projects/hooks/useInputAnalysisWorkflow";
import type { AnalysisSummary } from "../../../../types/api-artifacts";

describe("useInputAnalysisWorkflow", () => {
  it("starts with default idle state", () => {
    const { result } = renderHook(() => useInputAnalysisWorkflow());
    expect(result.current.state.uploadState).toBe("idle");
    expect(result.current.state.analysisState).toBe("idle");
    expect(result.current.state.currentStep).toBe("idle");
    expect(result.current.state.message).toBe("");
    expect(result.current.state.setupCompleted).toBe(false);
    expect(result.current.isUploading).toBe(false);
    expect(result.current.isAnalyzing).toBe(false);
  });

  it("markUploadRunning sets uploading state", () => {
    const { result } = renderHook(() => useInputAnalysisWorkflow());

    act(() => {
      result.current.markUploadRunning();
    });

    expect(result.current.state.uploadState).toBe("running");
    expect(result.current.state.currentStep).toBe("uploading");
    expect(result.current.state.message).toBe("Uploading documents...");
    expect(result.current.isUploading).toBe(true);
  });

  it("markUploadSuccess sets success state with summary", () => {
    const { result } = renderHook(() => useInputAnalysisWorkflow());
    const summary = { attemptedDocuments: 3, parsedDocuments: 2, failedDocuments: 1, failures: [] };

    act(() => {
      result.current.markUploadSuccess(summary);
    });

    expect(result.current.state.uploadState).toBe("success");
    expect(result.current.state.currentStep).toBe("idle");
    expect(result.current.state.uploadSummary).toEqual(summary);
    expect(result.current.state.lastUploadedAt).not.toBeNull();
  });

  it("markUploadError sets error state", () => {
    const { result } = renderHook(() => useInputAnalysisWorkflow());

    act(() => {
      result.current.markUploadError("Upload failed: timeout");
    });

    expect(result.current.state.uploadState).toBe("error");
    expect(result.current.state.currentStep).toBe("idle");
    expect(result.current.state.message).toBe("Upload failed: timeout");
  });

  it("markAnalysisRunning sets analyzing state", () => {
    const { result } = renderHook(() => useInputAnalysisWorkflow());

    act(() => {
      result.current.markAnalysisRunning();
    });

    expect(result.current.state.analysisState).toBe("running");
    expect(result.current.state.currentStep).toBe("analyzing");
    expect(result.current.state.message).toBe("Analysis in progress...");
    expect(result.current.isAnalyzing).toBe(true);
  });

  it("markAnalysisSuccess sets setupCompleted when summary has success status", () => {
    const { result } = renderHook(() => useInputAnalysisWorkflow());
    const summary = { status: "success" } as unknown as AnalysisSummary;

    act(() => {
      result.current.markAnalysisSuccess(summary);
    });

    expect(result.current.state.analysisState).toBe("success");
    expect(result.current.state.setupCompleted).toBe(true);
    expect(result.current.state.lastAnalyzedAt).not.toBeNull();
  });

  it("markAnalysisSuccess does not set setupCompleted when summary is null", () => {
    const { result } = renderHook(() => useInputAnalysisWorkflow());

    act(() => {
      result.current.markAnalysisSuccess(null);
    });

    expect(result.current.state.setupCompleted).toBe(false);
  });

  it("markAnalysisError sets error state", () => {
    const { result } = renderHook(() => useInputAnalysisWorkflow());

    act(() => {
      result.current.markAnalysisError("Analysis failed: crash");
    });

    expect(result.current.state.analysisState).toBe("error");
    expect(result.current.state.currentStep).toBe("idle");
    expect(result.current.state.message).toBe("Analysis failed: crash");
  });

  it("clearWorkflowMessage clears message", () => {
    const { result } = renderHook(() => useInputAnalysisWorkflow());

    act(() => {
      result.current.markUploadRunning();
    });
    expect(result.current.state.message).not.toBe("");

    act(() => {
      result.current.clearWorkflowMessage();
    });
    expect(result.current.state.message).toBe("");
  });
});
