import { lazy } from "react";
import { useProjectContext } from "../../context/ProjectContext";

const DocumentsPanel = lazy(() =>
  import("../../components/DocumentsPanel").then((m) => ({
    default: m.DocumentsPanel,
  })),
);

export function DocumentsTabAdapter() {
  const {
    selectedProject,
    textRequirements,
    setTextRequirements,
    handleSaveTextRequirements,
    files,
    setFiles,
    handleUploadDocuments,
    handleAnalyzeDocuments,
    loading,
    loadingMessage,
  } = useProjectContext();

  if (!selectedProject) return null;

  return (
    <DocumentsPanel
      selectedProject={selectedProject}
      textRequirements={textRequirements}
      onTextRequirementsChange={setTextRequirements}
      onSaveTextRequirements={handleSaveTextRequirements}
      files={files}
      onFilesChange={setFiles}
      onUploadDocuments={handleUploadDocuments}
      onAnalyzeDocuments={handleAnalyzeDocuments}
      loading={loading}
      loadingMessage={loadingMessage}
    />
  );
}
