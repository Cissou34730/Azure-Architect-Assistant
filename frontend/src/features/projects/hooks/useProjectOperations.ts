import { Project, ProjectState } from "../../../types/api";
import { useDocumentUpload } from "./useDocumentUpload";
import { useDocumentAnalysis } from "./useDocumentAnalysis";
import { useRequirementHandlers } from "./useRequirementHandlers";

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
    onComplete?: () => void
  ) => void;
  readonly setActiveTab: (tabId: string) => void;
  readonly success: (msg: string) => void;
  readonly showError: (msg: string) => void;
  readonly warning: (msg: string) => void;
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
  setActiveTab,
  success,
  showError,
  warning,
}: UseProjectOperationsProps) {
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
    setActiveTab,
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
