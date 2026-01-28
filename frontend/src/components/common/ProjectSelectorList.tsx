import { Project } from "../../types/api";
import { ProjectSelectorDropdownItem } from "./ProjectSelectorDropdownItem";

interface ProjectSelectorListProps {
  readonly loading: boolean;
  readonly filteredProjects: readonly Project[];
  readonly currentProjectId?: string;
  readonly highlightedIndex: number;
  readonly onSelect: (project: Project) => void;
  readonly onDelete: (e: React.MouseEvent, project: Project) => void;
  readonly setHighlightedIndex: (index: number) => void;
}

export function ProjectSelectorList({
  loading,
  filteredProjects,
  currentProjectId,
  highlightedIndex,
  onSelect,
  onDelete,
  setHighlightedIndex,
}: ProjectSelectorListProps) {
  if (loading) {
    return (
      <div className="p-4 space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          // eslint-disable-next-line react/no-array-index-key -- Static loading skeleton
          <div key={i} className="animate-pulse">
            <div className="h-14 bg-gray-100 rounded-lg" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="py-2 max-h-[400px] overflow-y-auto">
      {filteredProjects.map((project, index) => (
        <ProjectSelectorDropdownItem
          key={project.id}
          project={project}
          isActive={currentProjectId === project.id}
          isHighlighted={index === highlightedIndex}
          onSelect={onSelect}
          onDelete={onDelete}
          onMouseEnter={() => {
            setHighlightedIndex(index);
          }}
        />
      ))}
    </div>
  );
}
