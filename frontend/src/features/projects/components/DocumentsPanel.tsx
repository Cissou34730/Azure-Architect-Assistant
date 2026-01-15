import { Project } from "../../../types/api";
import { TextRequirements } from "./DocumentsPanel/TextRequirements";
import { FileUpload } from "./DocumentsPanel/FileUpload";
import { AnalyzeButton } from "./DocumentsPanel/AnalyzeButton";

interface DocumentsPanelProps {
  readonly selectedProject: Project;
  readonly textRequirements: string;
  readonly onTextRequirementsChange: (text: string) => void;
  readonly onSaveTextRequirements: () => void;
  readonly files: FileList | null;
  readonly onFilesChange: (files: FileList | null) => void;
  readonly onUploadDocuments: (e: React.FormEvent) => void;
  readonly onAnalyzeDocuments: () => void;
  readonly loading: boolean;
  readonly loadingMessage: string;
}

export function DocumentsPanel({
  selectedProject,
  textRequirements,
  onTextRequirementsChange,
  onSaveTextRequirements,
  files,
  onFilesChange,
  onUploadDocuments,
  onAnalyzeDocuments,
  loading,
  loadingMessage,
}: DocumentsPanelProps) {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Documents & Requirements</h2>

      <TextRequirements
        text={textRequirements}
        onChange={onTextRequirementsChange}
        onSave={onSaveTextRequirements}
        loading={loading}
      />

      <FileUpload
        files={files}
        onFilesChange={onFilesChange}
        onUpload={onUploadDocuments}
        loading={loading}
      />

      <AnalyzeButton
        selectedProject={selectedProject}
        textRequirements={textRequirements}
        onAnalyze={onAnalyzeDocuments}
        loading={loading}
        loadingMessage={loadingMessage}
      />
    </div>
  );
}
