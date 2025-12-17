import { useState, useEffect } from "react";

interface Project {
  id: string;
  name: string;
  textRequirements: string;
  createdAt: string;
}

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadProjects = async () => {
    setIsLoading(true);
    try {
      const response = await fetch("http://localhost:8080/api/projects");
      const data = await response.json();
      setProjects(data.projects || []);
    } catch (error) {
      console.error("Failed to load projects:", error);
      setProjects([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadProjects();
  }, []);

  return { projects, isLoading, refreshProjects: loadProjects };
}
