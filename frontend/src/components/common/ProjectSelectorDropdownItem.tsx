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

      <button
        onClick={(e) => { onDelete(e, project); }}
        disabled={!allowDelete}
        className={`p-2 rounded-lg opacity-0 group-hover:opacity-100 transition-all ${
          allowDelete
            ? "text-gray-400 hover:text-red-600 hover:bg-red-50"
            : "text-gray-300 cursor-not-allowed"
        }`}
        aria-label={allowDelete ? "Delete project" : "Delete project (coming soon)"}
        title={allowDelete ? "Delete project" : "Delete (coming soon)"}
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}
