import { useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
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
    (project: Project) => {
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
      return Promise.resolve(true);
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
