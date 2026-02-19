import { useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { projectApi } from "../services/projectService";
import { Project } from "../types/api";
import { useProjectsData } from "./useProjectsData";

export function useProjectSelector() {
  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId: string }>();
  const { state, setState, fetchProjects } = useProjectsData(projectId);

  const switchProject = useCallback(
    (project: Project) => {
      setState((prev) => ({ ...prev, currentProject: project }));
      void navigate(`/project/${project.id}`);
    },
    [navigate, setState],
  );

  const deleteProject = useCallback(
    async (project: Project): Promise<boolean> => {
      try {
        // Call API to soft delete the project
        await projectApi.delete(project.id);

        // Update client-side state after successful API call
        setState((prev) => {
          const nextProjects = prev.projects.filter((p) => p.id !== project.id);
          const isCurrent = prev.currentProject?.id === project.id;
          if (isCurrent) {
            void navigate("/project");
          }
          return {
            ...prev,
            projects: nextProjects,
            currentProject: isCurrent ? null : prev.currentProject,
          };
        });
        return true;
      } catch (error) {
        // Error is already handled by fetchWithErrorHandling
        // which will show a toast notification
        console.error("Failed to delete project:", error);
        return false;
      }
    },
    [navigate, setState],
  );

  return {
    ...state,
    switchProject,
    deleteProject,
    createNewProject: () => { void navigate("/project"); },
    refetchProjects: fetchProjects,
  };
}
