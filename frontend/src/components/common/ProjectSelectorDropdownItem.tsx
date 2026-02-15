import { Project } from "../../types/api";
import { Folder, Check, Trash2 } from "lucide-react";

interface ProjectSelectorDropdownItemProps {
  readonly project: Project;
  readonly isActive: boolean;
  readonly isHighlighted: boolean;
  readonly onSelect: (project: Project) => void;
  readonly onDelete: (e: React.MouseEvent, project: Project) => void;
  readonly onMouseEnter: () => void;
  readonly allowDelete: boolean;
}

export function ProjectSelectorDropdownItem({
  project,
  isActive,
  isHighlighted,
  onSelect,
  onDelete,
  onMouseEnter,
  allowDelete,
}: ProjectSelectorDropdownItemProps) {
  return (
    <div
      onClick={() => { onSelect(project); }}
      onMouseEnter={onMouseEnter}
      className={`w-full flex items-center gap-3 px-4 py-3 transition-colors group cursor-pointer ${
        isHighlighted ? "bg-surface" : ""
      } ${isActive ? "bg-brand-soft" : ""} hover:bg-surface`}
    >
      <div className="w-8 h-8 rounded-lg bg-brand-soft flex items-center justify-center shrink-0">
        <Folder className="h-4 w-4 text-brand" />
      </div>

      <div className="flex-1 min-w-0 text-left">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground truncate">
            {project.name}
          </span>
          {isActive && <Check className="h-4 w-4 text-brand shrink-0" />}
        </div>
        <p className="text-xs text-dim truncate">
          Updated {new Date(project.createdAt).toLocaleDateString()}
        </p>
      </div>

      <button
        onClick={(e) => { onDelete(e, project); }}
        disabled={!allowDelete}
        className={`p-2 rounded-lg opacity-0 group-hover:opacity-100 transition-all ${
          allowDelete
            ? "text-dim hover:text-danger hover:bg-danger-soft"
            : "text-border cursor-not-allowed"
        }`}
        aria-label={allowDelete ? "Delete project" : "Delete project (coming soon)"}
        title={allowDelete ? "Delete project" : "Delete (coming soon)"}
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}



