/**
 * Custom hooks for project management
 */

import { useState, useCallback } from "react";
import { Project, projectApi } from "../../../services/apiService";

export const useProjects = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchProjects = useCallback(async () => {
    try {
      const fetchedProjects = await projectApi.fetchAll();
      setProjects(fetchedProjects);
    } catch (error) {
      console.error("Error fetching projects:", error);
    }
  }, []);

  const createProject = useCallback(async (name: string) => {
    if (!name.trim()) {
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

  const uploadDocuments = useCallback(
    async (files: FileList) => {
      if (!selectedProject) {
        throw new Error("No project selected");
      }

      setLoading(true);
      try {
        await projectApi.uploadDocuments(selectedProject.id, files);
      } finally {
        setLoading(false);
      }
    },
    [selectedProject]
  );

  const saveTextRequirements = useCallback(
    async (text: string) => {
      if (!selectedProject) {
        throw new Error("No project selected");
      }

      setLoading(true);
      try {
        const updatedProject = await projectApi.saveTextRequirements(
          selectedProject.id,
          text
        );
        setProjects((prev) =>
          prev.map((p) => (p.id === updatedProject.id ? updatedProject : p))
        );
        setSelectedProject(updatedProject);
        return updatedProject;
      } finally {
        setLoading(false);
      }
    },
    [selectedProject]
  );

  return {
    projects,
    selectedProject,
    setSelectedProject,
    loading,
    fetchProjects,
    createProject,
    uploadDocuments,
    saveTextRequirements,
  };
};
