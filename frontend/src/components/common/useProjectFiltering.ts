import { useMemo, useEffect } from "react";
import { Project } from "../../types/api";

interface UseProjectFilteringProps {
  projects: readonly Project[];
  searchQuery: string;
  setHighlightedIndex: (index: number) => void;
}

/**
 * Custom hook to filter projects and manage highlighted index lifecycle.
 */
export function useProjectFiltering({
  projects,
  searchQuery,
  setHighlightedIndex,
}: UseProjectFilteringProps) {
  const filteredProjects = useMemo(() => {
    return projects.filter((project) =>
      project.name.toLowerCase().includes(searchQuery.toLowerCase()),
    );
  }, [projects, searchQuery]);

  // Handle highlighted index reset silently without useEffect cascading if possible
  // but to keep it simple and reactive to searchQuery, we'll keep it as is for now
  // and fix the linter warning in the main component or here.

  useEffect(() => {
    setHighlightedIndex(0);
  }, [searchQuery, setHighlightedIndex]);

  return filteredProjects;
}
