import { useCallback } from "react";
import { projectApi } from "../../../services/projectService";
import { Project } from "../../../types/api";

interface UseRequirementHandlersProps {
  selectedProject: Project | null;
  setSelectedProject: (p: Project | null) => void;
  textRequirements: string;
  refreshState: () => void | Promise<void>;
  generateProposal: (id: string, cb: () => void) => void | Promise<void>;
  success: (msg: string) => void;
  showError: (msg: string) => void;
}

export function useRequirementHandlers({
  selectedProject,
  setSelectedProject,
  textRequirements,
  refreshState,
  generateProposal,
  success,
  showError,
}: UseRequirementHandlersProps) {
  const handleSaveTextRequirements = useCallback(async (): Promise<void> => {
    if (selectedProject === null) {
      return;
    }
    try {
      const updated = await projectApi.saveTextRequirements(
        selectedProject.id,
        textRequirements,
      );
      setSelectedProject(updated);
      success("Requirements saved successfully!");
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Save failed";
      showError(`Error: ${msg}`);
    }
  }, [
    selectedProject,
    textRequirements,
    setSelectedProject,
    success,
    showError,
  ]);

  const handleGenerateProposal = useCallback((): void => {
    if (selectedProject === null) {
      return;
    }

    void generateProposal(selectedProject.id, () => {
      void refreshState();
    });
  }, [selectedProject, generateProposal, refreshState]);

  return { handleSaveTextRequirements, handleGenerateProposal };
}
