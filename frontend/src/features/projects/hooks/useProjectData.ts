import { useState, useEffect } from "react";
import { projectApi } from "../../../services/projectService";
import { Project } from "../../../types/api";
import { useToast } from "../../../hooks/useToast";

export function useProjectData(projectId: string | undefined) {
  const { error: showError } = useToast();
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [loadingProject, setLoadingProject] = useState(false);
  const [textRequirements, setTextRequirements] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);

  useEffect(() => {
    if (projectId === undefined || projectId === "") {
      setSelectedProject(null);
      return;
    }

    const fetchProject = async () => {
      setLoadingProject(true);
      try {
        const project = await projectApi.get(projectId);
        setSelectedProject(project);
        setTextRequirements(project.textRequirements ?? "");
      } catch (error) {
        const msg = error instanceof Error ? error.message : "Load failed";
        showError(`Failed to load project details: ${msg}`);
      } finally {
        setLoadingProject(false);
      }
    };

    void fetchProject();
  }, [projectId, showError]);

  return {
    selectedProject,
    setSelectedProject,
    loadingProject,
    textRequirements,
    setTextRequirements,
    files,
    setFiles,
  };
}
