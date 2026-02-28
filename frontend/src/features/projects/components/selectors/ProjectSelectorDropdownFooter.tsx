import { Plus } from "lucide-react";

interface ProjectSelectorDropdownFooterProps {
  readonly onCreateNew: () => void;
}

export function ProjectSelectorDropdownFooter({ onCreateNew }: ProjectSelectorDropdownFooterProps) {
  return (
    <div className="p-2 bg-surface border-t border-border">
      <button
        onClick={onCreateNew}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-brand hover:bg-brand-soft/50 rounded-lg transition-colors"
      >
        <Plus className="h-4 w-4" />
        New Project
      </button>
    </div>
  );
}

