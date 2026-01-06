import { ProjectTab } from "../types";
import { useProjectContext } from "../../context/ProjectContext";
import { DocumentsPanel } from "../../components/DocumentsPanel";

const DocumentsComponent = () => {
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
};

export const documentsTab: ProjectTab = {
  id: "documents",
  label: "Documents",
  path: "documents",
  component: DocumentsComponent,
};
