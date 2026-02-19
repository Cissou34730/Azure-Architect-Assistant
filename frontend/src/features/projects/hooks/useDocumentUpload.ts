import { useCallback } from "react";
import { projectApi } from "../../../services/projectService";
import { Project } from "../../../types/api";

interface UseDocumentUploadProps {
  readonly selectedProject: Project | null;
  readonly files: FileList | null;
  readonly setFiles: (f: FileList | null) => void;
  readonly success: (msg: string) => void;
  readonly showError: (msg: string) => void;
}

export function useDocumentUpload({
  selectedProject,
  files,
  setFiles,
  success,
  showError,
}: UseDocumentUploadProps) {
  const handleUploadDocuments = useCallback(
    async (e: React.SyntheticEvent): Promise<void> => {
      e.preventDefault();
      if (files === null || files.length === 0 || selectedProject === null) {
        return;
      }

      try {
        await projectApi.uploadDocuments(selectedProject.id, files);
        success("Documents uploaded successfully!");
        setFiles(null);
        const fileInput = document.getElementById("file-input");
        if (fileInput instanceof HTMLInputElement) {
          fileInput.value = "";
        }
      } catch (error) {
        const msg = error instanceof Error ? error.message : "Upload failed";
        showError(`Error: ${msg}`);
      }
    },
    [selectedProject, files, setFiles, success, showError],
  );

  return { handleUploadDocuments };
}
