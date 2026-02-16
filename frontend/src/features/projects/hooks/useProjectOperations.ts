import { Project, ProjectState } from "../../../types/api";
import { projectApi } from "../../../services/projectService";
import { useRequirementHandlers } from "./useRequirementHandlers";
import { useToast } from "../../../hooks/useToast";
import { useInputAnalysisWorkflow } from "./useInputAnalysisWorkflow";

function normalizeUploadSummary(summary: ProjectState["projectDocumentStats"]) {
  return {
    attemptedDocuments: summary?.attemptedDocuments ?? 0,
    parsedDocuments: summary?.parsedDocuments ?? 0,
    failedDocuments: summary?.failedDocuments ?? 0,
    failures: summary?.failures ?? [],
  };
}

interface UseProjectOperationsProps {
  readonly selectedProject: Project | null;
  readonly setSelectedProject: (p: Project | null) => void;
  readonly projectState: ProjectState | null;
  readonly files: FileList | null;
  readonly setFiles: (files: FileList | null) => void;
  readonly textRequirements: string;
  readonly analyzeDocuments: () => Promise<ProjectState>;
  readonly refreshState: () => Promise<void>;
  readonly generateProposal: (
    projectId: string,
    onComplete?: () => void,
  ) => void;
}

export function useProjectOperations({
  selectedProject,
  setSelectedProject,
  projectState,
  files,
  setFiles,
  textRequirements,
  analyzeDocuments,
  refreshState,
  generateProposal,
}: UseProjectOperationsProps) {
  const { success, error: showError, warning } = useToast();
  const workflow = useInputAnalysisWorkflow();

  const handleUploadDocuments = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (files === null || files.length === 0 || selectedProject === null) {
      return;
    }

    workflow.markUploadRunning();
    try {
      const uploadResult = await projectApi.uploadDocuments(
        selectedProject.id,
        files,
      );
      success("Documents uploaded successfully!");
      workflow.markUploadSuccess(normalizeUploadSummary(uploadResult.uploadSummary));
      await refreshState();
      setFiles(null);
      const fileInput = document.getElementById("file-input");
      if (fileInput instanceof HTMLInputElement) {
        fileInput.value = "";
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Upload failed";
      workflow.markUploadError(`Upload failed: ${msg}`);
      showError(`Error: ${msg}`);
    }
  };

  const handleAnalyzeDocuments = async (): Promise<void> => {
    if (selectedProject === null) {
      return;
    }

    const hasText =
      selectedProject.textRequirements !== undefined &&
      selectedProject.textRequirements.trim() !== "";
    const hasSelectedFiles = files !== null && files.length > 0;
    const hasUsableUploadedDocuments =
      projectState?.referenceDocuments.some(
        (document) =>
          document.parseStatus === undefined || document.parseStatus === "parsed",
      ) ?? false;
    const hasFiles = hasSelectedFiles || hasUsableUploadedDocuments;

    if (!hasText && !hasFiles) {
      warning(
        "Please provide either text requirements or upload documents before analyzing.",
      );
      return;
    }

    workflow.markAnalysisRunning();
    try {
      const analyzedState = await analyzeDocuments();
      workflow.markAnalysisSuccess(analyzedState.analysisSummary ?? null);
      success("Analysis complete!");
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Analysis failed";
      workflow.markAnalysisError(`Analysis failed: ${msg}`);
      showError(`Error: ${msg}`);
    }
  };

  const { handleSaveTextRequirements, handleGenerateProposal } =
    useRequirementHandlers({
      selectedProject,
      setSelectedProject,
      textRequirements,
      refreshState,
      generateProposal,
      success,
      showError,
    });

  return {
    handleUploadDocuments,
    handleAnalyzeDocuments,
    handleSaveTextRequirements,
    handleGenerateProposal,
    inputWorkflow: workflow.state,
    isUploadingDocuments: workflow.isUploading,
    isAnalyzingDocuments: workflow.isAnalyzing,
    clearInputWorkflowMessage: workflow.clearWorkflowMessage,
  };
}
