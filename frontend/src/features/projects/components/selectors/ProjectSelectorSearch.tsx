import { Search, Folder } from "lucide-react";
import { RefObject } from "react";

interface ProjectSelectorSearchProps {
  readonly searchQuery: string;
  readonly onSearchChange: (value: string) => void;
  readonly searchInputRef: RefObject<HTMLInputElement | null>;
  readonly loading: boolean;
  readonly hasProjects: boolean;
  readonly isSearching: boolean;
}

export function ProjectSelectorSearch({
  searchQuery,
  onSearchChange,
  searchInputRef,
  loading,
  hasProjects,
  isSearching,
}: ProjectSelectorSearchProps) {
  return (
    <>
      <div className="p-3 border-b border-border">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-dim" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => {
              onSearchChange(e.target.value);
            }}
            placeholder="Search projects..."
            className="w-full pl-10 pr-4 py-2 text-sm border border-border-stronger rounded-lg focus:outline-none focus:ring-2 focus:ring-brand"
            aria-label="Search projects"
          />
        </div>
      </div>

      {!hasProjects && !loading && (
        <div className="p-8 text-center">
          <Folder className="h-12 w-12 text-border mx-auto mb-3" />
          <p className="text-sm text-secondary mb-1">
            {isSearching
              ? "No projects match your search"
              : "No projects yet"}
          </p>
          {!isSearching && (
            <p className="text-xs text-dim">
              Create your first project to get started
            </p>
          )}
        </div>
      )}
    </>
  );
}

