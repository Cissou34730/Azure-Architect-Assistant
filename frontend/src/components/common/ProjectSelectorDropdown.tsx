import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from "react";
import { ChevronDown, Search, Folder, Trash2, Plus, Check } from "lucide-react";
import { Project } from "../../types/api";

interface ProjectSelectorDropdownProps {
  readonly projects: readonly Project[];
  readonly currentProject: Project | null;
  readonly onProjectSelect: (project: Project) => void;
  readonly onProjectDelete: (project: Project) => void;
  readonly onCreateNew: () => void;
  readonly loading?: boolean;
}

export interface ProjectSelectorDropdownRef {
  open: () => void;
  close: () => void;
  toggle: () => void;
}

export const ProjectSelectorDropdown = forwardRef<
  ProjectSelectorDropdownRef,
  ProjectSelectorDropdownProps
>(function ProjectSelectorDropdown(
  {
    projects,
    currentProject,
    onProjectSelect,
    onProjectDelete,
    onCreateNew,
    loading = false,
  },
  ref
) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Expose methods to parent via ref
  useImperativeHandle(ref, () => ({
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
    toggle: () => setIsOpen((prev) => !prev),
  }));

  // Filter projects based on search
  const filteredProjects = projects.filter((project) =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      // Focus search input when dropdown opens
      setTimeout(() => searchInputRef.current?.focus(), 100);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setHighlightedIndex((prev) =>
            prev < filteredProjects.length - 1 ? prev + 1 : prev
          );
          break;
        case "ArrowUp":
          e.preventDefault();
          setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : 0));
          break;
        case "Enter":
          e.preventDefault();
          if (filteredProjects[highlightedIndex]) {
            handleSelect(filteredProjects[highlightedIndex]);
          }
          break;
        case "Escape":
          e.preventDefault();
          setIsOpen(false);
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, highlightedIndex, filteredProjects]);

  // Reset highlighted index when search changes
  useEffect(() => {
    setHighlightedIndex(0);
  }, [searchQuery]);

  const handleSelect = (project: Project) => {
    onProjectSelect(project);
    setIsOpen(false);
    setSearchQuery("");
  };

  const handleDelete = (e: React.MouseEvent, project: Project) => {
    e.stopPropagation();
    onProjectDelete(project);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-60"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label="Project selector"
      >
        <Folder className="h-4 w-4 text-gray-600 shrink-0" />
        <span className="flex-1 text-left text-sm font-medium text-gray-900 truncate">
          {currentProject?.name || "Select a project"}
        </span>
        <ChevronDown
          className={`h-4 w-4 text-gray-600 shrink-0 transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          className="absolute top-full left-0 mt-2 w-full sm:w-[400px] bg-white rounded-lg shadow-lg border border-gray-200 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200"
        >
          {/* Search Input */}
          <div className="p-3 border-b border-gray-200">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search projects..."
                className="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label="Search projects"
              />
            </div>
          </div>

          {/* Project List */}
          <div className="max-h-[400px] overflow-y-auto">
            {loading ? (
              <div className="p-4 space-y-2">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="h-14 bg-gray-100 rounded-lg" />
                  </div>
                ))}
              </div>
            ) : filteredProjects.length === 0 ? (
              <div className="p-8 text-center">
                <Folder className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-600 mb-1">
                  {searchQuery ? "No projects match your search" : "No projects yet"}
                </p>
                {!searchQuery && (
                  <p className="text-xs text-gray-500">Create your first project to get started</p>
                )}
              </div>
            ) : (
              <div className="py-2">
                {filteredProjects.map((project, index) => {
                  const isActive = currentProject?.id === project.id;
                  const isHighlighted = index === highlightedIndex;

                  return (
                    <div
                      key={project.id}
                      onClick={() => handleSelect(project)}
                      onMouseEnter={() => setHighlightedIndex(index)}
                      className={`w-full flex items-center gap-3 px-4 py-3 transition-colors group cursor-pointer ${
                        isHighlighted ? "bg-gray-50" : ""
                      } ${isActive ? "bg-blue-50" : ""} hover:bg-gray-50`}
                    >
                      <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center shrink-0">
                        <Folder className="h-4 w-4 text-blue-600" />
                      </div>

                      <div className="flex-1 min-w-0 text-left">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-900 truncate">
                            {project.name}
                          </span>
                          {isActive && <Check className="h-4 w-4 text-blue-600 shrink-0" />}
                        </div>
                        <p className="text-xs text-gray-500 truncate">
                          Updated {new Date(project.createdAt).toLocaleDateString()}
                        </p>
                      </div>

                      {/* Delete Button */}
                      {!isActive && (
                        <button
                          onClick={(e) => handleDelete(e, project)}
                          className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-red-50 transition-all"
                          aria-label={`Delete ${project.name}`}
                        >
                          <Trash2 className="h-4 w-4 text-red-600" />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Create New Button */}
          <div className="p-3 border-t border-gray-200">
            <button
              onClick={() => {
                onCreateNew();
                setIsOpen(false);
              }}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
            >
              <Plus className="h-4 w-4" />
              Create New Project
            </button>
          </div>
        </div>
      )}
    </div>
  );
});
