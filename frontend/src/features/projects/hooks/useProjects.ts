/**
 * Custom hooks for project management
 */

import { useState, useCallback } from "react";
import { Project } from "../../../types/api";
import { projectApi } from "../../../services/projectService";

export const useProjects = () => {
  const [projects, setProjects] = useState<readonly Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchProjects = useCallback(async () => {
    try {
      const fetchedProjects = await projectApi.fetchAll();
      setProjects(fetchedProjects);
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Fetch failed";
      console.error(`Error fetching projects: ${msg}`);
    }
  }, []);

  const createProject = useCallback(async (name: string) => {
    if (name.trim() === "") {
      throw new Error("Project name is required");
    }

    setLoading(true);
    try {
      const project = await projectApi.create(name);
      setProjects((prev) => [...prev, project]);
      setSelectedProject(project);
      return project;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    projects,
    selectedProject,
    setSelectedProject,
    loading,
    fetchProjects,
    createProject,
  };
};
