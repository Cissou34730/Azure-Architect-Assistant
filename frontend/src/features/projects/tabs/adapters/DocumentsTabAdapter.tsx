import { lazy } from "react";
import { useProjectContext } from "../../context/useProjectContext";

const DOCUMENTS_PANEL_LAZY = lazy(() =>
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

  if (selectedProject === null) {
    return null;
  }

  const DOCUMENTS_PANEL = DOCUMENTS_PANEL_LAZY;

  return (
    <DOCUMENTS_PANEL
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
