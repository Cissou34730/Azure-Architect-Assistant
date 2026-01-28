import { Plus } from "lucide-react";

interface ProjectSelectorDropdownFooterProps {
  readonly onCreateNew: () => void;
}

export function ProjectSelectorDropdownFooter({ onCreateNew }: ProjectSelectorDropdownFooterProps) {
  return (
    <div className="p-2 bg-gray-50 border-t border-gray-200">
      <button
        onClick={onCreateNew}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50/50 rounded-lg transition-colors"
      >
        <Plus className="h-4 w-4" />
        New Project
      </button>
    </div>
  );
}
