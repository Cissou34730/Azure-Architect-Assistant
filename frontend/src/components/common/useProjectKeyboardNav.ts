import { useEffect, useCallback } from "react";
import { Project } from "../../types/api";

interface UseProjectKeyboardNavProps {
  isOpen: boolean;
  filteredProjects: readonly Project[];
  highlightedIndex: number;
  setHighlightedIndex: (index: (prev: number) => number) => void;
  setIsOpen: (isOpen: boolean) => void;
  handleSelect: (project: Project) => void;
}

export function useProjectKeyboardNav({
  isOpen,
  filteredProjects,
  highlightedIndex,
  setHighlightedIndex,
  setIsOpen,
  handleSelect,
}: UseProjectKeyboardNavProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      const pLen = filteredProjects.length;
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setHighlightedIndex((p) => (p < pLen - 1 ? p + 1 : p));
          break;
        case "ArrowUp":
          e.preventDefault();
          setHighlightedIndex((p) => (p > 0 ? p - 1 : 0));
          break;
        case "Enter": {
          e.preventDefault();
          const target = filteredProjects[highlightedIndex];
          handleSelect(target);
          break;
        }
        case "Escape":
          e.preventDefault();
          setIsOpen(false);
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [
    isOpen,
    highlightedIndex,
    filteredProjects,
    handleSelect,
    setHighlightedIndex,
    setIsOpen,
  ]);

  const toggleDropdown = useCallback(() => {
    setIsOpen(!isOpen);
  }, [isOpen, setIsOpen]);

  return { toggleDropdown };
}
