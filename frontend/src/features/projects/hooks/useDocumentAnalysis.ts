import { useCallback } from "react";
import { Project, ProjectState } from "../../../types/api";

interface UseDocumentAnalysisProps {
  readonly selectedProject: Project | null;
  readonly files: FileList | null;
  readonly analyzeDocuments: () => Promise<ProjectState>;
  readonly setActiveTab: (tabId: string) => void;
  readonly success: (msg: string) => void;
  readonly showError: (msg: string) => void;
  readonly warning: (msg: string) => void;
}

export function useDocumentAnalysis({
  selectedProject,
  files,
  analyzeDocuments,
  setActiveTab,
  success,
  showError,
  warning,
}: UseDocumentAnalysisProps) {
  const handleAnalyzeDocuments = useCallback(async (): Promise<void> => {
    if (selectedProject === null) {
      return;
    }

    const hasText =
      selectedProject.textRequirements !== undefined &&
      selectedProject.textRequirements.trim() !== "";
    const hasFiles = files !== null && files.length > 0;

    if (!hasText && !hasFiles) {
      warning(
        "Please provide either text requirements or upload documents before analyzing.",
      );
      return;
    }

    try {
      await analyzeDocuments();
      setActiveTab("state");
      success("Analysis complete!");
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Analysis failed";
      showError(`Error: ${msg}`);
    }
  }, [
    selectedProject,
    files,
    analyzeDocuments,
    setActiveTab,
    success,
    showError,
    warning,
  ]);

  return { handleAnalyzeDocuments };
}
