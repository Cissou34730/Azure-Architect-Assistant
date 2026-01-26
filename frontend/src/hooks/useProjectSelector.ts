import { useState, useEffect, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Project } from "../types/api";
import { projectApi } from "../services/projectService";

export function useProjectSelector() {
  const [projects, setProjects] = useState<readonly Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId: string }>();

  // Fetch all projects
  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const fetchedProjects = await projectApi.fetchAll();
      setProjects(fetchedProjects);

      // Set current project if we have a projectId in URL
      if (projectId) {
        const project = fetchedProjects.find(
          (p: Project) => p.id === projectId,
        );
        if (project) {
          setCurrentProject(project);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects");
      console.error("Error fetching projects:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  // Fetch projects on mount and when projectId changes
  useEffect(() => {
    void fetchProjects();
  }, [fetchProjects]);

  // Switch to a different project
  const switchProject = useCallback(
    (project: Project) => {
      setCurrentProject(project);
      navigate(`/projects/${project.id}`);
    },
    [navigate],
  );

  // Delete a project (with mock implementation for now)
  const deleteProject = useCallback(
    async (project: Project) => {
      try {
        // TODO: Implement actual API call when backend is ready
        // await projectService.deleteProject(project.id);

        // Mock implementation - just remove from local state
        setProjects((prev) => prev.filter((p) => p.id !== project.id));

        // If we're deleting the current project, navigate to projects list
        if (currentProject?.id === project.id) {
          setCurrentProject(null);
          navigate("/projects");
        }

        return true;
      } catch (err) {
        console.error("Error deleting project:", err);
        throw err;
      }
    },
    [currentProject, navigate],
  );

  // Create new project
  const createNewProject = useCallback(() => {
    // Navigate to projects page which has the create project UI
    navigate("/projects");
  }, [navigate]);

  return {
    projects,
    currentProject,
    loading,
    error,
    switchProject,
    deleteProject,
    createNewProject,
    refetchProjects: fetchProjects,
  };
}
