import { useCallback, useMemo, useState } from "react";
import type { AnalysisSummary, UploadSummary } from "../../../types/api";

export type WorkflowPhaseState = "idle" | "running" | "success" | "error";

export interface InputAnalysisWorkflowState {
  readonly uploadState: WorkflowPhaseState;
  readonly analysisState: WorkflowPhaseState;
  readonly currentStep: "idle" | "uploading" | "analyzing";
  readonly message: string;
  readonly lastUploadedAt: string | null;
  readonly lastAnalyzedAt: string | null;
  readonly uploadSummary: UploadSummary | null;
  readonly analysisSummary: AnalysisSummary | null;
  readonly setupCompleted: boolean;
}

const DEFAULT_WORKFLOW_STATE: InputAnalysisWorkflowState = {
  uploadState: "idle",
  analysisState: "idle",
  currentStep: "idle",
  message: "",
  lastUploadedAt: null,
  lastAnalyzedAt: null,
  uploadSummary: null,
  analysisSummary: null,
  setupCompleted: false,
};

interface WorkflowPatch {
  readonly uploadState?: WorkflowPhaseState;
  readonly analysisState?: WorkflowPhaseState;
  readonly currentStep?: "idle" | "uploading" | "analyzing";
  readonly message?: string;
  readonly lastUploadedAt?: string | null;
  readonly lastAnalyzedAt?: string | null;
  readonly uploadSummary?: UploadSummary | null;
  readonly analysisSummary?: AnalysisSummary | null;
  readonly setupCompleted?: boolean;
}

const UPLOAD_RUNNING_PATCH: WorkflowPatch = {
  uploadState: "running",
  currentStep: "uploading",
  message: "Uploading documents...",
};

const ANALYSIS_RUNNING_PATCH: WorkflowPatch = {
  analysisState: "running",
  currentStep: "analyzing",
  message: "Analysis in progress...",
};

function makeUploadSuccessPatch(uploadSummary: UploadSummary): WorkflowPatch {
  return {
    uploadState: "success",
    currentStep: "idle",
    message: "Documents uploaded. Ready to analyze.",
    lastUploadedAt: new Date().toISOString(),
    uploadSummary,
  };
}

function makeAnalysisSuccessPatch(analysisSummary: AnalysisSummary | null): WorkflowPatch {
  return {
    analysisState: "success",
    currentStep: "idle",
    message: "Analysis completed.",
    lastAnalyzedAt: new Date().toISOString(),
    analysisSummary,
    setupCompleted: analysisSummary !== null && analysisSummary.status === "success",
  };
}

export function useInputAnalysisWorkflow() {
  const [state, setState] = useState<InputAnalysisWorkflowState>(DEFAULT_WORKFLOW_STATE);

  const patchState = useCallback((patch: WorkflowPatch) => {
    setState((current) => ({ ...current, ...patch }));
  }, []);

  const markUploadRunning = useCallback(() => patchState(UPLOAD_RUNNING_PATCH), [patchState]);
  const markUploadSuccess = useCallback((s: UploadSummary) => patchState(makeUploadSuccessPatch(s)), [patchState]);
  const markUploadError = useCallback((message: string) => patchState({ uploadState: "error", currentStep: "idle", message }), [patchState]);
  const markAnalysisRunning = useCallback(() => patchState(ANALYSIS_RUNNING_PATCH), [patchState]);
  const markAnalysisSuccess = useCallback((s: AnalysisSummary | null) => patchState(makeAnalysisSuccessPatch(s)), [patchState]);
  const markAnalysisError = useCallback((message: string) => patchState({ analysisState: "error", currentStep: "idle", message }), [patchState]);
  const clearWorkflowMessage = useCallback(() => patchState({ message: "" }), [patchState]);

  return useMemo(
    () => ({
      state,
      isUploading: state.currentStep === "uploading",
      isAnalyzing: state.currentStep === "analyzing",
      markUploadRunning,
      markUploadSuccess,
      markUploadError,
      markAnalysisRunning,
      markAnalysisSuccess,
      markAnalysisError,
      clearWorkflowMessage,
    }),
    [state, markUploadRunning, markUploadSuccess, markUploadError, markAnalysisRunning, markAnalysisSuccess, markAnalysisError, clearWorkflowMessage],
  );
}
