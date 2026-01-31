import { useState, useRef, forwardRef, useImperativeHandle, useCallback } from "react";
import { ChevronDown, Folder } from "lucide-react";
import { Project } from "../../types/api";
import { ProjectSelectorDropdownFooter } from "./ProjectSelectorDropdownFooter";
import { ProjectSelectorSearch } from "./ProjectSelectorSearch";
import { ProjectSelectorList } from "./ProjectSelectorList";
import { useProjectFiltering } from "./useProjectFiltering";
import { useProjectKeyboardNav } from "./useProjectKeyboardNav";
import { useClickOutside } from "./useClickOutside";

interface ProjectSelectorDropdownProps {
  readonly projects: readonly Project[];
  readonly currentProject: Project | null;
  readonly onProjectSelect: (project: Project) => void;
  readonly onProjectDelete: (project: Project) => void;
  readonly onCreateNew: () => void;
  readonly loading?: boolean;
  readonly allowDelete?: boolean;
}

export interface ProjectSelectorDropdownRef {
  open: () => void;
  close: () => void;
  toggle: () => void;
}

// eslint-disable-next-line @typescript-eslint/naming-convention
const ProjectSelectorDropdownInternal = forwardRef<
  ProjectSelectorDropdownRef,
  ProjectSelectorDropdownProps
>(function ProjectSelectorDropdownInternal(
  {
    projects,
    currentProject,
    onProjectSelect,
    onProjectDelete,
    onCreateNew,
    loading = false,
    allowDelete = true,
  },
  ref
) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const filteredProjects = useProjectFiltering({
    projects,
    searchQuery,
    setHighlightedIndex,
  });

  const handleSelect = useCallback(
    (project: Project) => {
      onProjectSelect(project);
      setIsOpen(false);
      setSearchQuery("");
    },
    [onProjectSelect]
  );

  const { toggleDropdown } = useProjectKeyboardNav({
    isOpen,
    filteredProjects,
    highlightedIndex,
    setHighlightedIndex,
    setIsOpen,
    handleSelect,
  });

  useClickOutside({
    isOpen,
    setIsOpen,
    dropdownRef,
    searchInputRef,
  });

  useImperativeHandle(ref, () => ({
    open: () => {
      setIsOpen(true);
    },
    close: () => {
      setIsOpen(false);
    },
    toggle: toggleDropdown,
  }));

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={toggleDropdown}
        className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-60"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label="Project selector"
      >
        <Folder className="h-4 w-4 text-gray-600 shrink-0" />
        <span className="flex-1 text-left text-sm font-medium text-gray-900 truncate">
          {currentProject?.name ?? "Select a project"}
        </span>
        <ChevronDown
          className={`h-4 w-4 text-gray-600 shrink-0 transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {isOpen && (
        <ProjectSelectorMenu
          loading={loading}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          searchInputRef={searchInputRef}
          filteredProjects={filteredProjects}
          currentProjectId={currentProject?.id}
          highlightedIndex={highlightedIndex}
          setHighlightedIndex={setHighlightedIndex}
          onSelect={handleSelect}
          onProjectDelete={onProjectDelete}
          allowDelete={allowDelete}
          onCreateNew={onCreateNew}
        />
      )}
    </div>
  );
});

// eslint-disable-next-line @typescript-eslint/naming-convention
export const ProjectSelectorDropdown = ProjectSelectorDropdownInternal;

interface ProjectSelectorMenuProps {
  readonly loading: boolean;
  readonly searchQuery: string;
  readonly setSearchQuery: (value: string) => void;
  readonly searchInputRef: React.RefObject<HTMLInputElement>;
  readonly filteredProjects: readonly Project[];
  readonly currentProjectId?: string;
  readonly highlightedIndex: number;
  readonly setHighlightedIndex: (index: number) => void;
  readonly onSelect: (project: Project) => void;
  readonly onProjectDelete: (project: Project) => void;
  readonly allowDelete: boolean;
  readonly onCreateNew: () => void;
}

function ProjectSelectorMenu({
  loading,
  searchQuery,
  setSearchQuery,
  searchInputRef,
  filteredProjects,
  currentProjectId,
  highlightedIndex,
  setHighlightedIndex,
  onSelect,
  onProjectDelete,
  allowDelete,
  onCreateNew,
}: ProjectSelectorMenuProps) {
  return (
    <div className="absolute top-full left-0 mt-2 w-full sm:w-96 bg-white rounded-lg shadow-lg border border-gray-200 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
      <ProjectSelectorSearch
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        searchInputRef={searchInputRef}
        loading={loading}
        hasProjects={filteredProjects.length > 0}
        isSearching={searchQuery !== ""}
      />

      <ProjectSelectorList
        loading={loading}
        filteredProjects={filteredProjects}
        currentProjectId={currentProjectId}
        highlightedIndex={highlightedIndex}
        onSelect={onSelect}
        onDelete={(e, project) => {
          if (allowDelete) {
            e.stopPropagation();
            onProjectDelete(project);
          }
        }}
        setHighlightedIndex={setHighlightedIndex}
        allowDelete={allowDelete}
      />

      <ProjectSelectorDropdownFooter onCreateNew={onCreateNew} />
    </div>
  );
}
