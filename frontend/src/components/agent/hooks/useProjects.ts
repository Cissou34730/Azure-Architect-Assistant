import { useState, useEffect, useCallback } from "react";
import { agentApi } from "../../../services/agentService";
import type { Project } from "../../../types/agent";

export function useProjects() {
  const [projects, setProjects] = useState<readonly Project[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadProjects = useCallback(async () => {
    setIsLoading(true);
    try {
      const loadedProjects = await agentApi.getProjects();
      setProjects(loadedProjects);
    } catch (error) {
      console.error("Failed to load projects:", error);
      setProjects([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  return { projects, isLoading, refreshProjects: loadProjects };
}
