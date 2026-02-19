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

function isDocumentUsable(doc: { readonly parseStatus?: string }): boolean {
  return doc.parseStatus === undefined || doc.parseStatus === "parsed";
}

function hasAnalysisInputs(
  textRequirements: string | undefined,
  files: FileList | null,
  referenceDocuments: readonly { readonly parseStatus?: string }[] | undefined,
): boolean {
  const hasText = textRequirements !== undefined && textRequirements.trim() !== "";
  const hasSelectedFiles = files !== null && files.length > 0;
  const hasUsableUploaded = referenceDocuments?.some(isDocumentUsable) ?? false;
  return hasText || hasSelectedFiles || hasUsableUploaded;
}

interface UploadContext {
  readonly files: FileList | null;
  readonly project: Project | null;
  readonly setFiles: (files: FileList | null) => void;
  readonly refreshState: () => Promise<void>;
  readonly workflow: ReturnType<typeof useInputAnalysisWorkflow>;
  readonly success: (msg: string) => void;
  readonly showError: (msg: string) => void;
}

async function runUploadDocuments(e: React.SyntheticEvent, ctx: UploadContext): Promise<void> {
  e.preventDefault();
  if (ctx.files === null || ctx.files.length === 0 || ctx.project === null) return;
  ctx.workflow.markUploadRunning();
  try {
    const result = await projectApi.uploadDocuments(ctx.project.id, ctx.files);
    ctx.success("Documents uploaded successfully!");
    ctx.workflow.markUploadSuccess(normalizeUploadSummary(result.uploadSummary));
    await ctx.refreshState();
    ctx.setFiles(null);
    const input = document.getElementById("file-input");
    if (input instanceof HTMLInputElement) input.value = "";
  } catch (error) {
    const msg = error instanceof Error ? error.message : "Upload failed";
    ctx.workflow.markUploadError(`Upload failed: ${msg}`);
    ctx.showError(`Error: ${msg}`);
  }
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

  const handleUploadDocuments = (e: React.SyntheticEvent): Promise<void> =>
    runUploadDocuments(e, { files, project: selectedProject, setFiles, refreshState, workflow, success, showError });

  const handleAnalyzeDocuments = async (): Promise<void> => {
    if (selectedProject === null) return;
    if (!hasAnalysisInputs(selectedProject.textRequirements, files, projectState?.referenceDocuments)) {
      warning("Please provide either text requirements or upload documents before analyzing.");
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
