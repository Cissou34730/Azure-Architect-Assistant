import { Project, ProjectState } from "../../../types/api";
import { useDocumentUpload } from "./useDocumentUpload";
import { useDocumentAnalysis } from "./useDocumentAnalysis";
import { useRequirementHandlers } from "./useRequirementHandlers";
import { useToast } from "../../../hooks/useToast";

interface UseProjectOperationsProps {
  readonly selectedProject: Project | null;
  readonly setSelectedProject: (p: Project | null) => void;
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
  files,
  setFiles,
  textRequirements,
  analyzeDocuments,
  refreshState,
  generateProposal,
}: UseProjectOperationsProps) {
  const { success, error: showError, warning } = useToast();
  const { handleUploadDocuments } = useDocumentUpload({
    selectedProject,
    files,
    setFiles,
    success,
    showError,
  });

  const { handleAnalyzeDocuments } = useDocumentAnalysis({
    selectedProject,
    files,
    analyzeDocuments,
    success,
    showError,
    warning,
  });

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
  };
}
